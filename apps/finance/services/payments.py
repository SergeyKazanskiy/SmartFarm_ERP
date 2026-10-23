"""
Платежи (OP-FIN-15…17) + автоматическая проводка при проведении.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import FinanceEvents as FE

from apps.finance.models import FinancialTransaction, Invoice, Payment
from apps.finance.services.helpers import (
    DEFAULT_AP_ACCOUNT_CODE, DEFAULT_AR_ACCOUNT_CODE,
    DEFAULT_BANK_ACCOUNT_CODE, DEFAULT_CASH_ACCOUNT_CODE,
    find_account_by_code, gen_code,
)
from apps.finance.services.invoices import InvoiceService


class PaymentService:

    @staticmethod
    @transaction.atomic
    def plan(*, company_id: int, data: dict):
        """OP-FIN-15."""
        payment = Payment.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("PAY"),
            invoice_id=data.get("invoice_id"),
            bank_account_id=data.get("bank_account_id"),
            cash_account_id=data.get("cash_account_id"),
            payment_status="planned",
            payment_date=data["payment_date"],
            amount=data["amount"],
        )
        EventBus.publish(
            FE.PAYMENT_PLAN,
            company_id=company_id,
            payload={
                "payment_id": payment.id,
                "invoice_id": payment.invoice_id,
                "amount": float(payment.amount),
            },
        )
        return payment

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, payment_id: int):
        """
        OP-FIN-16 + OP-FIN-16a + OP-FIN-18 (автопроводка).
        planned → completed.
        - Пересчитать статус счёта (paid/partially_paid).
        - Создать проводку Дт/Кт.
        """
        payment = Payment.objects.select_for_update().get(
            pk=payment_id, company_id=company_id,
        )
        if payment.payment_status != "planned":
            raise ValueError(_("Провести можно только запланированный платёж"))

        payment.payment_status = "completed"
        payment.save(update_fields=["payment_status", "updated_at"])

        # Пересчёт статуса счёта
        if payment.invoice:
            InvoiceService._recalc_status(payment.invoice)

        # Автопроводка
        PaymentService._create_auto_transaction(payment)

        EventBus.publish(
            FE.PAYMENT_COMPLETE,
            company_id=company_id,
            payload={
                "payment_id": payment.id,
                "invoice_id": payment.invoice_id,
                "amount": float(payment.amount),
                "payment_status": payment.payment_status,
            },
        )
        return payment

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, payment_id: int):
        """OP-FIN-17."""
        payment = Payment.objects.select_for_update().get(
            pk=payment_id, company_id=company_id,
        )
        if payment.payment_status != "planned":
            raise ValueError(_("Отменить можно только запланированный платёж"))
        payment.payment_status = "cancelled"
        payment.save(update_fields=["payment_status", "updated_at"])

        EventBus.publish(
            FE.PAYMENT_CANCEL,
            company_id=company_id,
            payload={"payment_id": payment.id},
        )
        return payment

    @staticmethod
    def _create_auto_transaction(payment: Payment) -> None:
        """
        Автоматическая проводка при проведении платежа.

        Логика:
        - AP (кредиторский счёт — платим поставщику):
          Дт «Расчёты с поставщиками» (60) — Кт «Денежные средства» (51/50).
        - AR (дебиторский счёт — получаем от покупателя):
          Дт «Денежные средства» (51/50) — Кт «Расчёты с покупателями» (62).

        Если счета не найдены в плане — пропускаем проводку
        (в реальном проекте — можно бросать ошибку).
        """
        invoice = payment.invoice
        if invoice is None:
            return

        debit_account = None
        credit_account = None

        if invoice.invoice_type == "AP":
            debit_account = find_account_by_code(
                payment.company_id, DEFAULT_AP_ACCOUNT_CODE,
            )
            if payment.bank_account_id:
                credit_account = find_account_by_code(
                    payment.company_id, DEFAULT_BANK_ACCOUNT_CODE,
                )
            elif payment.cash_account_id:
                credit_account = find_account_by_code(
                    payment.company_id, DEFAULT_CASH_ACCOUNT_CODE,
                )
        elif invoice.invoice_type == "AR":
            credit_account = find_account_by_code(
                payment.company_id, DEFAULT_AR_ACCOUNT_CODE,
            )
            if payment.bank_account_id:
                debit_account = find_account_by_code(
                    payment.company_id, DEFAULT_BANK_ACCOUNT_CODE,
                )
            elif payment.cash_account_id:
                debit_account = find_account_by_code(
                    payment.company_id, DEFAULT_CASH_ACCOUNT_CODE,
                )

        if debit_account is None or credit_account is None:
            # Нет нужных счетов — проводку не создаём.
            return

        FinancialTransaction.objects.create(
            company_id=payment.company_id,
            code=gen_code("FT"),
            debit_account=debit_account,
            credit_account=credit_account,
            cost_center=None,
            payment=payment,
            amount=payment.amount,
            transaction_date=payment.payment_date or timezone.now(),
        )