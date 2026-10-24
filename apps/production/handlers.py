"""
Подписчики Production-модуля на события других модулей.

Реализовано:
- Sales.order.produce → создать ProductionOrder из Sales-заказа.

Заглушки:
- Sales.invoice.paid → закрыть связанный ProductionOrder (если был).
- PM.project.save → связать ProductionOrder с PM (через BOM).
"""
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.event_bus import DomainEvent, EventBus

from apps.production.models import Bom, ProductionOrder
from apps.production.services.helpers import gen_code

logger = logging.getLogger(__name__)


@EventBus.subscribe("Sales.order.produce")
@transaction.atomic
def on_sales_order_produce(event: DomainEvent) -> None:
    """
    Sales передал заказ в производство:
    - ищем BOM по product_material_id из позиции заказа;
    - создаём ProductionOrder в статусе draft;
    - если BOM не найден — лог + пропуск.
    """
    order_id = event.payload.get("order_id")
    production_order_id = event.payload.get("production_order_id")
    if not order_id:
        return

    from apps.sales.models import Order

    order = Order.objects.filter(
        pk=order_id, company_id=event.company_id,
    ).prefetch_related("lines").first()
    if order is None:
        return

    # Идемпотентность: если ProductionOrder уже создан — пропускаем
    if ProductionOrder.objects.filter(
        company_id=event.company_id, code=f"PROD-SO-{order.id}",
    ).exists():
        return

    # Ищем BOM по первому material_id из позиции заказа
    first_line = order.lines.first()
    if first_line is None:
        logger.warning(
            "Production: Sales order %s без позиций, ProductionOrder не создан",
            order.id,
        )
        return

    bom = Bom.objects.filter(
        company_id=event.company_id,
        product_material_id=first_line.material_id,
    ).first()
    if bom is None:
        logger.info(
            "Production: для material_id=%s нет BOM (order=%s), заказ не создан",
            first_line.material_id, order.id,
        )
        return

    # Сумма quantity по позициям = плановое количество
    from django.db.models import Sum
    total_qty = order.lines.aggregate(s=Sum("quantity"))["s"] or Decimal("0")

    ProductionOrder.objects.create(
        company_id=event.company_id,
        code=f"PROD-SO-{order.id}",
        bom=bom,
        routing_id=None,  # будет задан при подтверждении
        planned_quantity=total_qty,
        planned_start_date=timezone.now().date(),
        status="draft",
    )
    logger.info(
        "Production: создан ProductionOrder для Sales order %s (bom=%s, qty=%.2f)",
        order.id, bom.id, float(total_qty),
    )


# ============================================================
# Заглушки для будущих модулей
# ============================================================

# @EventBus.subscribe("Sales.invoice.paid")
# def on_sales_invoice_paid(event: DomainEvent) -> None:
#     """Оплата Sales → закрыть связанный ProductionOrder (если был)."""
#     ...

# @EventBus.subscribe("WMS.inventory.low_stock")
# def on_wms_low_stock(event: DomainEvent) -> None:
#     """Дефицит материала → создать заявку в Procurement."""
#     ...
    


# 9.1. apps/wms/handlers.py — добавить резервирование и приход

# python
# @EventBus.subscribe("Production.productionOrder.confirm")
# @transaction.atomic
# def on_production_order_confirm(event: DomainEvent) -> None:
#     """
#     ProductionOrder подтверждён → зарезервировать материалы по BOM.
#     Идемпотентность: один резерв на (production_order, material).
#     """
#     production_order_id = event.payload.get("production_order_id")
#     if not production_order_id:
#         return

#     from apps.production.models import ProductionOrder
#     from apps.wms.models import (
#         MaterialReservation, Warehouse,
#     )

#     order = ProductionOrder.objects.filter(
#         pk=production_order_id, company_id=event.company_id,
#     ).select_related("bom").first()
#     if order is None or order.bom is None:
#         return

#     warehouse = Warehouse.objects.filter(
#         company_id=event.company_id,
#     ).first()
#     if warehouse is None:
#         logger.warning(
#             "WMS: нет ни одного склада для company=%s", event.company_id,
#         )
#         return

#     for bom_item in order.bom.items.all():
#         # Пропускаем, если уже зарезервировано
#         exists = MaterialReservation.objects.filter(
#             company_id=event.company_id,
#             material_id=bom_item.material_id,
#             warehouse=warehouse,
#             task_object_type="production_order",
#             task_object_id=order.id,
#             status__in=["reserved", "issued"],
#         ).exists()
#         if exists:
#             continue

#         # qty_reserved = bom.quantity × planned_quantity
#         qty = bom_item.quantity * order.planned_quantity
#         MaterialReservation.objects.create(
#             company_id=event.company_id,
#             code=f"RES-PROD-{order.id}-{bom_item.material_id}",
#             material_id=bom_item.material_id,
#             warehouse=warehouse,
#             task_object_type="production_order",
#             task_object_id=order.id,
#             quantity=qty,
#             status="reserved",
#             reserved_at=timezone.now(),
#         )
#         logger.info(
#             "WMS: зарезервировано %.2f ед. material %s под ProductionOrder %s",
#             float(qty), bom_item.material_id, order.id,
#         )


# @EventBus.subscribe("Production.productionOrder.complete")
# @transaction.atomic
# def on_production_order_complete(event: DomainEvent) -> None:
#     """
#     ProductionOrder завершён → оприходовать готовую продукцию на склад.
#     """
#     production_order_id = event.payload.get("production_order_id")
#     bom_id = event.payload.get("bom_id")
#     planned_quantity = event.payload.get("planned_quantity")
#     if not production_order_id or not bom_id or planned_quantity is None:
#         return

#     from apps.production.models import Bom
#     from apps.wms.models import (
#         GoodsReceipt, GoodsReceiptLine,
#         Material, StorageLocation, Warehouse,
#     )

#     bom = Bom.objects.filter(
#         pk=bom_id, company_id=event.company_id,
#     ).first()
#     if bom is None:
#         return

#     warehouse = Warehouse.objects.filter(
#         company_id=event.company_id,
#     ).first()
#     if warehouse is None:
#         return

#     location = StorageLocation.objects.filter(
#         company_id=event.company_id, warehouse=warehouse,
#     ).first()
    # if location is None:
    #     return

    # material = Material.objects.filter(
    #     company_id=event.company_id, id=bom.product_material_id,
    # ).first()
    # if material is None:
    #     return

    # receipt = GoodsReceipt.objects.create(
    #     company_id=event.company_id,
    #     code=f"GR-PROD-{production_order_id}",
    #     warehouse=warehouse,
    #     counterparty_id=None,
    #     receipt_date=timezone.now(),
    #     status="draft",
    # )
    # GoodsReceiptLine.objects.create(
    #     company_id=event.company_id,
    #     code=f"GRL-PROD-{production_order_id}",
    #     receipt=receipt,
    #     material=material,
    #     location=location,
    #     quantity=Decimal(str(planned_quantity)),
    #     unit_cost=material.unit_cost if hasattr(material, "unit_cost") else None,
    # )
    # logger.info(
    #     "WMS: создан приход %s на %.2f ед. material %s (ProductionOrder %s)",
    #     receipt.code, float(planned_quantity), material.id, production_order_id,
    # )


# apps/finance/handlers.py — добавить расчёт себестоимости

# python
# @EventBus.subscribe("Production.productionOrder.complete")
# @transaction.atomic
# def on_production_order_complete(event: DomainEvent) -> None:
#     """
#     ProductionOrder завершён → рассчитать себестоимость выпуска.
#     Пока — создаём FinancialIndicator с indicator_code='cogs_prod_<id>'.
#     Реальная себестоимость (материалы + труд + накладные) будет считаться
#     в модуле APS/HR, а здесь фиксируем факт.
#     """
#     production_order_id = event.payload.get("production_order_id")
#     if not production_order_id:
#         return

#     from apps.finance.models import FinancialIndicator
#     from apps.production.models import ProductionOrder

#     order = ProductionOrder.objects.filter(
#         pk=production_order_id, company_id=event.company_id,
#     ).select_related("bom").first()
#     if order is None or order.bom is None:
#         return

#     # Себестоимость = Σ (bom_item.quantity × bom_item.unit_cost) × planned_qty
#     from decimal import Decimal
#     cogs = Decimal("0")
#     for item in order.bom.items.all():
#         if item.unit_cost is not None:
#             cogs += item.quantity * item.unit_cost * order.planned_quantity

#     if cogs <= 0:
#         return

#     # Идемпотентность
#     code = f"FI-PROD-{order.id}"
#     if FinancialIndicator.objects.filter(
#         company_id=event.company_id, code=code,
#     ).exists():
#         return

#     FinancialIndicator.objects.create(
#         company_id=event.company_id,
#         code=code,
#         financial_project=None,
#         period=None,
#         indicator_code=f"cogs_prod_{order.id}",
#         indicator_value=cogs,
#     )
#     logger.info(
#         "FIN: рассчитана себестоимость ProductionOrder %s: %.2f",
#         order.id, float(cogs),
#     )