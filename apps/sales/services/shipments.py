"""
Отгрузки (OP-SALES-19…22, OP-SALES-23).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import OrderLine, Shipment, ShipmentLine
from apps.sales.services.helpers import gen_code
from apps.sales.services.orders import OrderService


class ShipmentService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-SALES-19."""
        shipment = Shipment.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SHIP"),
            shipment_number=data["shipment_number"],
            order_id=data["order_id"],
            warehouse_id=data.get("warehouse_id"),
            shipment_date=data["shipment_date"],
            status="planned",
            tracking_number=data.get("tracking_number", ""),
            shipping_method_id=data.get("shipping_method_id"),
        )

        EventBus.publish(
            SE.SHIPMENT_CREATE,
            company_id=company_id,
            payload={
                "shipment_id": shipment.id,
                "order_id": shipment.order_id,
            },
        )
        return shipment

    @staticmethod
    @transaction.atomic
    def ship(*, company_id: int, shipment_id: int):
        """
        OP-SALES-21 + OP-SALES-23 + OP-SALES-24.
        planned → shipped.
        Пересчёт order_line.shipped_quantity по всем линиям отгрузки.
        Если все позиции заказа отгружены — order → completed.
        """
        shipment = Shipment.objects.select_for_update().get(
            pk=shipment_id, company_id=company_id,
        )
        if shipment.status != "planned":
            raise ValueError(_("Отгрузить можно только запланированную отгрузку"))

        shipment.status = "shipped"
        shipment.save(update_fields=["status", "updated_at"])

        # OP-SALES-23: пересчёт shipped_quantity для всех позиций заказа
        order = shipment.order
        for order_line in order.lines.all():
            shipped = (
                ShipmentLine.objects.filter(
                    company_id=company_id,
                    order_line=order_line,
                    shipment__status__in=["shipped", "delivered"],
                ).aggregate(s=Sum("quantity"))["s"] or Decimal("0")
            )
            if order_line.shipped_quantity != shipped:
                order_line.shipped_quantity = shipped
                order_line.save(update_fields=["shipped_quantity"])

        # OP-SALES-24: попытка завершить заказ
        OrderService._try_complete(order)

        EventBus.publish(
            SE.SHIPMENT_DELIVER,
            company_id=company_id,
            payload={"shipment_id": shipment.id, "order_id": order.id},
        )
        return shipment

    @staticmethod
    @transaction.atomic
    def deliver(*, company_id: int, shipment_id: int):
        """OP-SALES-22. shipped → delivered."""
        shipment = Shipment.objects.select_for_update().get(
            pk=shipment_id, company_id=company_id,
        )
        if shipment.status != "shipped":
            raise ValueError(_("Доставить можно только отгруженную"))
        shipment.status = "delivered"
        shipment.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.SHIPMENT_DELIVER,
            company_id=company_id,
            payload={
                "shipment_id": shipment.id,
                "order_id": shipment.order_id,
                "action": "delivered",
            },
        )
        return shipment


class ShipmentLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-SALES-20."""
        line = ShipmentLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SHL"),
            shipment_id=data["shipment_id"],
            order_line_id=data["order_line_id"],
            quantity=data["quantity"],
        )

        EventBus.publish(
            SE.SHIPMENT_LINE_CREATE,
            company_id=company_id,
            payload={
                "shipment_line_id": line.id,
                "shipment_id": line.shipment_id,
            },
        )
        return line