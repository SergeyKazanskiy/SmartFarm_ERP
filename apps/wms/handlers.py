"""
Подписчики WMS-модуля на события других модулей.

Реализовано:
- Sales.shipment.create → WMS создаёт InventoryTransaction (списание)
  для каждой позиции отгрузки, если может найти остаток по material_id.
- CP.blacklist.add → логирование (заглушка для реальной блокировки).
"""
import logging
from decimal import Decimal

from django.db import transaction

from core.event_bus import DomainEvent, EventBus

from apps.wms.models import Inventory
from apps.wms.services.inventory import InventoryTransactionService

logger = logging.getLogger(__name__)


@EventBus.subscribe("Sales.shipment.create")
@transaction.atomic
def on_sales_shipment_create(event: DomainEvent) -> None:
    """
    Отгрузка Sales → списание остатков WMS.
    Упрощённая логика: ищем Inventory по material_id, списываем quantity.
    """
    shipment_id = event.payload.get("shipment_id")
    order_id = event.payload.get("order_id")
    if not shipment_id:
        return

    from apps.sales.models import Shipment
    shipment = Shipment.objects.filter(
        pk=shipment_id, company_id=event.company_id,
    ).first()
    if shipment is None:
        return

    for sh_line in shipment.lines.select_related("order_line").all():
        material_id = sh_line.order_line.material_id
        qty = sh_line.quantity or Decimal("0")
        if qty <= 0:
            continue

        inv = Inventory.objects.select_for_update().filter(
            company_id=event.company_id,
            material_id=material_id,
        ).order_by("-quantity").first()

        if inv is None:
            logger.warning(
                "WMS: не найден остаток для material_id=%s (shipment=%s)",
                material_id, shipment_id,
            )
            continue

        # Списываем, но не уходим в минус
        actual_qty = min(qty, inv.quantity)
        if actual_qty <= 0:
            continue

        inv.quantity -= actual_qty
        inv.save(update_fields=["quantity", "updated_at"])

        InventoryTransactionService.record(
            company_id=event.company_id,
            inventory=inv,
            transaction_type="issue",
            quantity=-actual_qty,
            source_document_type="sales_shipment",
            source_document_id=shipment.id,
        )

        logger.info(
            "WMS: списано %.2f из %s (shipment=%s, order=%s)",
            float(actual_qty), material_id, shipment_id, order_id,
        )


@EventBus.subscribe("CP.blacklist.add")
def on_cp_blacklist_add(event: DomainEvent) -> None:
    """
    Контрагент в чёрном списке.
    Пока только логируем — реальные заказы уже отменены в Sales/PM.
    TODO: приостановить приходы от заблокированного поставщика.
    """
    counterparty_id = event.payload.get("counterparty_id")
    if counterparty_id:
        logger.info(
            "WMS: blacklisted counterparty %s — приходы приостановлены (todo)",
            counterparty_id,
        )