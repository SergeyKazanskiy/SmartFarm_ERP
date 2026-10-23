"""
Счета (OP-FIN-11…14).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import FinanceEvents as FE

from apps.finance.models import Invoice, InvoiceLine
from apps.finance.services.helpers import gen_code


class InvoiceService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-11."""
        invoice = Invoice.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("FINV"),
            invoice_type=data["invoice_type"],
            counterparty_id=data["counterparty_id"],
            contract_id=data.get("contract_id"),
            source_object_type=data.get("source_object_type", ""),
            source_object_id=data.get("source_object_id"),
            invoice_number=data.get("invoice_number", ""),
            invoice_date=data["invoice_date"],
            due_date=data.get("due_date"),
            amount=data["amount"],
            currency_id=data.get("currency_id"),
            status="draft",
        )
        EventBus.publish(
            FE.INVOICE_CREATE,
            company_id=company_id,
            payload={
                "invoice_id": invoice.id,
                "invoice_type": invoice.invoice_type,
                "counterparty_id": invoice.counterparty_id,
                "amount": float(invoice.amount),
                "source_object_type": invoice.source_object_type,
                "source_object_id": invoice.source_object_id,
            },
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def issue(*, company_id: int, invoice_id: int):
        """OP-FIN-13. draft → issued."""
        invoice = Invoice.objects.select_for_update().get(
            pk=invoice_id, company_id=company_id,
        )
        if invoice.status != "draft":
            raise ValueError(_("Выставить можно только черновик счёта"))
        invoice.status = "issued"
        invoice.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            FE.INVOICE_ISSUE,
            company_id=company_id,
            payload={
                "invoice_id": invoice.id,
                "invoice_type": invoice.invoice_type,
                "counterparty_id": invoice.counterparty_id,
                "amount": float(invoice.amount),
            },
        )
        return invoice

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, invoice_id: int):
        """OP-FIN-14. draft/issued → cancelled."""
        invoice = Invoice.objects.select_for_update().get(
            pk=invoice_id, company_id=company_id,
        )
        if invoice.status not in ("draft", "issued"):
            raise ValueError(_("Отменить можно только счёт в статусе draft или issued"))
        invoice.status = "cancelled"
        invoice.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            FE.INVOICE_CANCEL,
            company_id=company_id,
            payload={"invoice_id": invoice.id},
        )
        return invoice

    @staticmethod
    def _recalc_status(invoice: Invoice) -> None:
        """
        Пересчёт статуса по сумме проведённых платежей.
        Соответствует SQL OP-FIN-16a.
        """
        from apps.finance.models import Payment
        paid = (
            Payment.objects.filter(
                invoice=invoice, payment_status="completed",
            ).aggregate(s=Sum("amount"))["s"] or Decimal("0")
        )
        if paid >= invoice.amount and invoice.amount > 0:
            new_status = "paid"
        elif paid > 0:
            new_status = "partially_paid"
        else:
            # Если уже был issued/overdue — оставляем, иначе вернёмся в issued
            new_status = invoice.status if invoice.status in ("issued", "overdue") else "issued"
        if new_status != invoice.status:
            invoice.status = new_status
            invoice.save(update_fields=["status", "updated_at"])


class InvoiceLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-12."""
        line = InvoiceLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("FINVL"),
            invoice_id=data["invoice_id"],
            description=data["description"],
            amount=data["amount"],
        )
        EventBus.publish(
            FE.INVOICE_LINE_CREATE,
            company_id=company_id,
            payload={"invoice_line_id": line.id, "invoice_id": line.invoice_id},
        )
        return line