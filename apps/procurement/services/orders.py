"""
Заказы поставщикам (OP-PROC-12…19) + история + поставки.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import ProcurementEvents as PE

from apps.procurement.models import (
    Delivery, Order, OrderHistory, OrderLine,
)
from apps.procurement.services.helpers import calc_line_total, gen_code


class OrderHistoryService:
    """Запись в историю заказа. Вызывается из OrderService при смене статуса."""

    @staticmethod
    def record(
        *,
        order: Order,
        status_from: str,
        status_to: str,
        actor_employee_id: int | None = None,
        comment: str = "",
    ) -> OrderHistory:
        return OrderHistory.objects.create(
            company_id=order.company_id,
            code=gen_code("HIST"),
            order=order,
            changed_at=timezone.now(),
            changed_by_employee_id=actor_employee_id,
            status_from=status_from,
            status_to=status_to,
            comment=comment,
        )


class OrderService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict,
               actor_employee_id: int | None = None):
        """OP-PROC-12."""
        order = Order.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("PO"),
            order_number=data["order_number"],
            supplier_id=data["supplier_id"],
            requisition_id=data.get("requisition_id"),
            rfq_id=data.get("rfq_id"),
            order_date=data["order_date"],
            expected_delivery_date=data.get("expected_delivery_date"),
            status="draft",
            total_amount=Decimal("0"),
            currency_id=data.get("currency_id"),
            created_by_employee_id=actor_employee_id,
        )
        OrderHistoryService.record(
            order=order, status_from="", status_to="draft",
            actor_employee_id=actor_employee_id, comment="created",
        )
        EventBus.publish(
            PE.ORDER_CREATE,
            company_id=company_id,
            payload={
                "order_id": order.id,
                "supplier_id": order.supplier_id,
                "order_number": order.order_number,
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def send(*, company_id: int, order_id: int,
             actor_employee_id: int | None = None):
        """OP-PROC-15: draft → sent."""
        order = Order.objects.select_for_update().get(
            pk=order_id, company_id=company_id,
        )
        if order.status != "draft":
            raise ValueError(_("Отправить можно только черновик"))
        old = order.status
        order.status = "sent"
        order.save(update_fields=["status", "updated_at"])
        OrderHistoryService.record(
            order=order, status_from=old, status_to="sent",
            actor_employee_id=actor_employee_id,
        )
        return order

    @staticmethod
    @transaction.atomic
    def confirm(*, company_id: int, order_id: int,
                actor_employee_id: int | None = None):
        """
        OP-PROC-16: sent → confirmed.
        Публикует событие ORDER_CONFIRM — FIN создаст AP-счёт.
        """
        order = Order.objects.select_for_update().get(
            pk=order_id, company_id=company_id,
        )
        if order.status != "sent":
            raise ValueError(_("Подтвердить можно только отправленный заказ"))
        old = order.status
        order.status = "confirmed"
        order.save(update_fields=["status", "updated_at"])
        OrderHistoryService.record(
            order=order, status_from=old, status_to="confirmed",
            actor_employee_id=actor_employee_id,
        )

        EventBus.publish(
            PE.ORDER_CONFIRM,
            company_id=company_id,
            payload={
                "order_id": order.id,
                "supplier_id": order.supplier_id,
                "total_amount": float(order.total_amount) if order.total_amount else None,
                "currency_id": order.currency_id,
                "order_date": order.order_date.isoformat(),
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def receive(
        *,
        company_id: int,
        order_id: int,
        order_line_id: int,
        received_quantity,
        delivery_date,
        actor_employee_id: int | None = None,
    ):
        """
        OP-PROC-17 / OP-PROC-18.
        - увеличить received_quantity в позиции заказа
        - создать Delivery
        - пересчитать статус заказа:
          * все получены → completed + событие ORDER_RECEIVE_COMPLETE
          * частично → partially_received
        """
        order = Order.objects.select_for_update().get(
            pk=order_id, company_id=company_id,
        )
        if order.status not in ("confirmed", "partially_received"):
            raise ValueError(
                _("Принимать можно только confirmed / partially_received")
            )

        line = OrderLine.objects.select_for_update().get(
            pk=order_line_id, order=order, company_id=company_id,
        )
        line.received_quantity = (
            (line.received_quantity or Decimal("0"))
            + Decimal(str(received_quantity))
        )
        line.save(update_fields=["received_quantity", "updated_at"])

        Delivery.objects.create(
            company_id=company_id,
            code=gen_code("DEL"),
            order=order,
            delivery_date=delivery_date,
            quantity=received_quantity,
            status="received",
        )

        old = order.status
        all_received = not order.lines.filter(
            received_quantity__lt=F("quantity"),
        ).exists()

        if all_received:
            order.status = "completed"
            order.actual_delivery_date = delivery_date
            order.save(update_fields=[
                "status", "actual_delivery_date", "updated_at",
            ])
            OrderHistoryService.record(
                order=order, status_from=old, status_to="completed",
                actor_employee_id=actor_employee_id,
            )
            # Событие для WMS — создать goods_receipt
            EventBus.publish(
                PE.ORDER_RECEIVE_COMPLETE,
                company_id=company_id,
                payload={
                    "order_id": order.id,
                    "supplier_id": order.supplier_id,
                    "delivery_date": delivery_date.isoformat(),
                },
            )
        else:
            order.status = "partially_received"
            order.save(update_fields=["status", "updated_at"])
            OrderHistoryService.record(
                order=order, status_from=old, status_to="partially_received",
                actor_employee_id=actor_employee_id,
            )

        EventBus.publish(
            PE.ORDER_RECEIVE,
            company_id=company_id,
            payload={
                "order_id": order.id,
                "order_line_id": line.id,
                "received_quantity": float(received_quantity),
                "status": order.status,
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, order_id: int,
               actor_employee_id: int | None = None):
        """OP-PROC-19."""
        order = Order.objects.select_for_update().get(
            pk=order_id, company_id=company_id,
        )
        if order.status not in ("draft", "sent"):
            raise ValueError(_("Отменить можно только draft / sent"))
        old = order.status
        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])
        OrderHistoryService.record(
            order=order, status_from=old, status_to="cancelled",
            actor_employee_id=actor_employee_id,
        )
        EventBus.publish(
            PE.ORDER_CANCEL,
            company_id=company_id,
            payload={"order_id": order.id},
        )
        return order

    @staticmethod
    def _recalc_total(order: Order) -> None:
        total = (
            order.lines.aggregate(s=Sum("total_price"))["s"] or Decimal("0")
        )
        order.total_amount = total
        order.save(update_fields=["total_amount", "updated_at"])


class OrderLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROC-13. Авторасчёт total_price."""
        line = OrderLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("POL"),
            order_id=data["order_id"],
            material_id=data["material_id"],
            quantity=data["quantity"],
            unit_price=data["unit_price"],
            received_quantity=Decimal("0"),
        )
        line.total_price = calc_line_total(line.quantity, line.unit_price)
        line.save(update_fields=["total_price"])
        OrderService._recalc_total(line.order)

        EventBus.publish(
            PE.ORDER_LINE_CREATE,
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
    def update(*, company_id: int, line_id: int, data: dict):
        """OP-PROC-14."""
        line = OrderLine.objects.select_for_update().get(
            pk=line_id, company_id=company_id,
        )
        if line.order.status != "draft":
            raise ValueError(_("Редактировать можно только черновик"))
        for field in ("quantity", "unit_price"):
            if field in data:
                setattr(line, field, data[field])
        line.total_price = calc_line_total(line.quantity, line.unit_price)
        line.save()
        OrderService._recalc_total(line.order)
        EventBus.publish(
            PE.ORDER_LINE_UPDATE,
            company_id=company_id,
            payload={"order_line_id": line.id},
        )
        return line


class DeliveryService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """Создание поставки напрямую (не через receive)."""
        return Delivery.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("DEL"),
            order_id=data["order_id"],
            delivery_date=data["delivery_date"],
            quantity=data["quantity"],
            status=data.get("status", "received"),
        )