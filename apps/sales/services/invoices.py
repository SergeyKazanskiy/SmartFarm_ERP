"""
Счета (OP-SALES-29…31).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import Invoice
from apps.sales.services.helpers import gen_code


class InvoiceService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-SALES-29. total_amount = order.total_amount."""
        order = data["order"]
        invoice = Invoice.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SINV"),
            invoice_number=data["invoice_number"],
            order=order,
            invoice_date=data["invoice_date"],
            due_date=data.get("due_date"),
            total_amount=order.total_amount or Decimal("0"),
            status="draft",
            paid_amount=Decimal("0"),
        )

        EventBus.publish(
            SE.INVOICE_CREATE,
            company_id=company_id,
            payload={
                "invoice_id": invoice.id,
                "order_id": order.id,
                "total_amount": float(invoice.total_amount),
            },
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def send(*, company_id: int, invoice_id: int):
        """OP-SALES-30. draft → sent."""
        inv = Invoice.objects.select_for_update().get(
            pk=invoice_id, company_id=company_id,
        )
        if inv.status != "draft":
            raise ValueError(_("Отправить можно только черновик"))
        inv.status = "sent"
        inv.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.INVOICE_SEND,
            company_id=company_id,
            payload={"invoice_id": inv.id, "order_id": inv.order_id},
        )
        return inv

    @staticmethod
    @transaction.atomic
    def pay(*, company_id: int, invoice_id: int, paid_amount):
        """
        OP-SALES-31.
        Накопительно: paid_amount += сумма, status = paid при полной оплате.
        """
        inv = Invoice.objects.select_for_update().get(
            pk=invoice_id, company_id=company_id,
        )
        current_paid = inv.paid_amount or Decimal("0")
        new_paid = current_paid + Decimal(str(paid_amount))
        inv.paid_amount = new_paid

        if inv.total_amount and new_paid >= inv.total_amount:
            inv.status = "paid"
        else:
            inv.status = "sent"

        inv.save(update_fields=["paid_amount", "status", "updated_at"])

        EventBus.publish(
            SE.INVOICE_PAY,
            company_id=company_id,
            payload={
                "invoice_id": inv.id,
                "order_id": inv.order_id,
                "paid_amount": float(new_paid),
                "status": inv.status,
            },
        )
        return inv