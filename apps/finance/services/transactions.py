"""
Проводки (OP-FIN-18).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus
from core.events import FinanceEvents as FE

from apps.finance.models import FinancialTransaction
from apps.finance.services.helpers import gen_code


class FinancialTransactionService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-18. Двойная запись."""
        if data["debit_account_id"] == data["credit_account_id"]:
            raise ValueError("Дт и Кт не могут совпадать")

        tx = FinancialTransaction.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("FT"),
            debit_account_id=data["debit_account_id"],
            credit_account_id=data["credit_account_id"],
            cost_center_id=data.get("cost_center_id"),
            payment_id=data.get("payment_id"),
            amount=data["amount"],
            transaction_date=data.get("transaction_date") or timezone.now(),
        )
        EventBus.publish(
            FE.FINANCIAL_TRANSACTION_CREATE,
            company_id=company_id,
            payload={
                "transaction_id": tx.id,
                "debit_account_id": tx.debit_account_id,
                "credit_account_id": tx.credit_account_id,
                "amount": float(tx.amount),
            },
        )
        return tx