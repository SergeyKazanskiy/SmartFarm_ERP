"""
Заказы клиентов (OP-SALES-13…18, OP-SALES-23…24).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import Order, OrderLine
from apps.sales.services.helpers import calc_line_total, gen_code


class OrderService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict,
               actor_employee_id: int | None = None):
        """OP-SALES-13."""
        order = Order.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SO"),
            order_number=data["order_number"],
            customer_id=data["customer_id"],
            quote_id=data.get("quote_id"),
            order_date=data["order_date"],
            order_type=data.get("order_type", "regular"),
            status="draft",
            currency_id=data.get("currency_id"),
            expected_ship_date=data.get("expected_ship_date"),
            delivery_address_id=data.get("delivery_address_id"),
            created_by_employee_id=actor_employee_id,
            total_amount=Decimal("0"),
        )

        EventBus.publish(
            SE.ORDER_CREATE,
            company_id=company_id,
            payload={
                "order_id": order.id,
                "customer_id": order.customer_id,
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def confirm(*, company_id: int, order_id: int):
        """OP-SALES-15. draft → confirmed."""
        o = Order.objects.select_for_update().get(
            pk=order_id, company_id=company_id,
        )
        if o.status != "draft":
            raise ValueError(_("Подтвердить можно только черновик заказа"))
        o.status = "confirmed"
        o.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.ORDER_CREATE,
            company_id=company_id,
            payload={"order_id": o.id, "action": "confirm"},
        )
        return o

    @staticmethod
    @transaction.atomic
    def produce(*, company_id: int, order_id: int, production_order_id: int):
        """OP-SALES-16. confirmed → in_production."""
        o = Order.objects.select_for_update().get(
            pk=order_id, company_id=company_id,
        )
        if o.status != "confirmed":
            raise ValueError(_("Передать в производство можно только подтверждённый заказ"))
        o.status = "in_production"
        o.production_order_id = production_order_id
        o.save(update_fields=[
            "status", "production_order_id", "updated_at",
        ])

        EventBus.publish(
            SE.ORDER_PRODUCE,
            company_id=company_id,
            payload={
                "order_id": o.id,
                "production_order_id": production_order_id,
            },
        )
        return o

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, order_id: int):
        """OP-SALES-18."""
        o = Order.objects.select_for_update().get(
            pk=order_id, company_id=company_id,
        )
        if o.status not in ("draft", "confirmed"):
            raise ValueError(_("Отменить можно только заказ в статусе draft или confirmed"))
        o.status = "cancelled"
        o.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.ORDER_CANCEL,
            company_id=company_id,
            payload={"order_id": o.id},
        )
        return o

    @staticmethod
    def _recalc_total(order: Order) -> None:
        total = (
            order.lines.aggregate(s=Sum("total_price"))["s"] or Decimal("0")
        )
        order.total_amount = total
        order.save(update_fields=["total_amount", "updated_at"])

    @staticmethod
    def _try_complete(order: Order) -> bool:
        """
        OP-SALES-24: если все позиции отгружены — order.status=completed.
        Возвращает True, если заказ завершён.
        """
        remaining = order.lines.filter(
            shipped_quantity__lt=models.F("quantity"),
        ).exists()
        if not remaining:
            from django.utils import timezone
            order.status = "completed"
            order.actual_ship_date = timezone.now().date()
            order.save(update_fields=[
                "status", "actual_ship_date", "updated_at",
            ])
            EventBus.publish(
                SE.ORDER_UPDATE_STATUS,
                company_id=order.company_id,
                payload={"order_id": order.id, "status": "completed"},
            )
            return True
        return False


class OrderLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-SALES-14. Авторасчёт total_price + пересчёт order.total_amount."""
        line = OrderLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SOL"),
            order_id=data["order_id"],
            material_id=data["material_id"],
            quantity=data["quantity"],
            unit_price=data["unit_price"],
            discount_percent=data.get("discount_percent", 0),
            shipped_quantity=Decimal("0"),
        )
        line.total_price = calc_line_total(
            line.quantity, line.unit_price, line.discount_percent,
        )
        line.save(update_fields=["total_price"])
        OrderService._recalc_total(line.order)

        EventBus.publish(
            SE.ORDER_LINE_CREATE,
            company_id=company_id,
            payload={
                "order_line_id": line.id,
                "order_id": line.order_id,
                "total_price": float(line.total_price),
            },
        )
        return line

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, line_id: int):
        line = OrderLine.objects.get(pk=line_id, company_id=company_id)
        order = line.order
        line.delete()
        OrderService._recalc_total(order)


# Импорт models здесь, чтобы не выносить в шапку
from django.db import models  # noqa: E402