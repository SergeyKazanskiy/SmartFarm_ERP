"""
Подписчики Procurement-модуля на события других модулей.

Реализовано:
- WMS.material.updateReorderPoint — лог (можно автоматически создавать заявки).

Заглушки:
- WMS.inventory.low_stock (когда появится) → создать requisition.
- Production.material.required → создать requisition.
"""
import logging

from core.event_bus import DomainEvent, EventBus

logger = logging.getLogger(__name__)


@EventBus.subscribe("WMS.material.updateReorderPoint")
def on_wms_reorder_point_changed(event: DomainEvent) -> None:
    """
    Изменена точка перезаказа — потенциально нужно проверить дефицит.
    Пока только логируем.
    """
    logger.info(
        "PROC: получено обновление min_stock_level для material %s (company=%s)",
        event.payload.get("material_id"), event.company_id,
    )


# ============================================================
# Заглушки для будущих модулей
# ============================================================

# @EventBus.subscribe("WMS.inventory.low_stock")
# def on_wms_low_stock(event: DomainEvent) -> None:
#     """Остаток упал ниже min_stock_level → создать заявку на закупку."""
#     ...

# @EventBus.subscribe("Production.material.required")
# def on_prod_material_required(event: DomainEvent) -> None:
#     """Production нуждается в материале → создать заявку на закупку."""
#     ...
    

# В существующий apps/finance/handlers.py добавьте:

# python
# @EventBus.subscribe("Procurement.order.confirm")
# @transaction.atomic
# def on_procurement_order_confirm(event: DomainEvent) -> None:
#     """
#     Заказ поставщику подтверждён → создать AP-счёт на сумму заказа.
#     """
#     order_id = event.payload.get("order_id")
#     supplier_id = event.payload.get("supplier_id")
#     total_amount = event.payload.get("total_amount")
#     if not order_id or not supplier_id or total_amount is None:
#         return

#     # Резолвим supplier.counterparty_id
#     from apps.procurement.models import Order, Supplier
#     order = Order.objects.filter(
#         pk=order_id, company_id=event.company_id,
#     ).select_related("supplier").first()
#     if order is None or order.supplier is None:
#         return

#     # Идемпотентность: один AP-счёт на заказ
#     if Invoice.objects.filter(
#         company_id=event.company_id,
#         source_object_type="procurement_order",
#         source_object_id=order.id,
#         invoice_type="AP",
#     ).exists():
#         return

#     Invoice.objects.create(
#         company_id=event.company_id,
#         code=gen_code("FINV"),
#         invoice_type="AP",
#         counterparty_id=order.supplier.counterparty_id,
#         contract_id=None,
#         source_object_type="procurement_order",
#         source_object_id=order.id,
#         invoice_number=f"AP-{order.order_number}",
#         invoice_date=order.order_date,
#         due_date=order.expected_delivery_date,
#         amount=Decimal(str(total_amount)),
#         currency_id=order.currency_id,
#         status="draft",
#     )
#     logger.info(
#         "FIN: создан AP-счёт по заказу поставщику %s (company=%s)",
#         order.id, event.company_id,
#     )
# Импорты в начале apps/finance/handlers.py уже есть (Invoice, Payment, gen_code, Decimal, transaction). Ничего дополнительно добавлять не нужно.
    


# apps/wms/handlers.py — добавить слушателя Procurement

# В существующий apps/wms/handlers.py добавьте:

# python
# @EventBus.subscribe("Procurement.order.receive_complete")
# @transaction.atomic
# def on_procurement_order_received(event: DomainEvent) -> None:
#     """
#     Заказ поставщику полностью получен → создать приход в WMS
#     по каждой позиции заказа.
#     """
#     order_id = event.payload.get("order_id")
#     delivery_date = event.payload.get("delivery_date")
#     if not order_id:
#         return

#     from apps.procurement.models import Order
#     from apps.wms.models import (
#         GoodsReceipt, GoodsReceiptLine, Material,
#         StorageLocation, Warehouse,
#     )

#     order = Order.objects.filter(
#         pk=order_id, company_id=event.company_id,
#     ).prefetch_related("lines").first()
#     if order is None:
#         return

#     # Идемпотентность: один приход на заказ
#     exists = GoodsReceipt.objects.filter(
#         company_id=event.company_id,
#         counterparty_id=order.supplier.counterparty_id,
#         receipt_date__date=delivery_date,
#     ).exists()
#     if exists:
#         return

#     # Склад по умолчанию — первый склад компании
#     warehouse = Warehouse.objects.filter(
#         company_id=event.company_id,
#     ).first()
#     if warehouse is None:
#         logger.warning("WMS: нет ни одного склада для company=%s", event.company_id)
#         return

#     default_location = StorageLocation.objects.filter(
#         company_id=event.company_id, warehouse=warehouse,
#     ).first()
#     if default_location is None:
#         logger.warning("WMS: нет ячеек на складе %s", warehouse.id)
#         return

#     receipt = GoodsReceipt.objects.create(
#         company_id=event.company_id,
#         code=gen_code("GR"),
#         warehouse=warehouse,
#         counterparty_id=order.supplier.counterparty_id,
#         receipt_date=delivery_date,
#         status="draft",
#     )

#     from datetime import datetime
#     for line in order.lines.all():
#         material = Material.objects.filter(
#             company_id=event.company_id, id=line.material_id,
#         ).first()
#         if material is None:
#             continue
#         GoodsReceiptLine.objects.create(
#             company_id=event.company_id,
#             code=gen_code("GRL"),
#             receipt=receipt,
#             material=material,
#             location=default_location,
#             quantity=line.received_quantity,
#             unit_cost=line.unit_price,
#         )

#     logger.info(
#         "WMS: создан приход GR-%s по заказу поставщику %s",
#         receipt.code, order.id,
#     )
# Важно: в apps/wms/handlers.py уже есть импорты DomainEvent, EventBus, transaction, logger. Нужно добавить импорт gen_code (from apps.wms.services.helpers import gen_code), если он ещё не импортирован. Иначе — импортировать внутри функции.