"""
Справочники Finance: план счетов, ЦЗ, финпроекты, кассы, банк-счета, курсы.
OP-FIN-01…06.
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import FinanceEvents as FE

from apps.finance.models import (
    BankAccount, CashAccount, CostCenter, ExchangeRate, FinAccount,
    FinancialProject,
)
from apps.finance.services.helpers import gen_code


class AccountService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-01."""
        acc = FinAccount.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("ACC"),
            account_code=data["account_code"],
            account_name=data["account_name"],
            account_type=data["account_type"],
        )
        EventBus.publish(
            FE.ACCOUNT_CREATE,
            company_id=company_id,
            payload={"account_id": acc.id, "account_code": acc.account_code},
        )
        return acc


class CostCenterService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-02."""
        cc = CostCenter.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("CC"),
            name=data["name"],
        )
        EventBus.publish(
            FE.COST_CENTER_CREATE,
            company_id=company_id,
            payload={"cost_center_id": cc.id, "name": cc.name},
        )
        return cc


class FinancialProjectService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-06."""
        fp = FinancialProject.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("FP"),
            name=data["name"],
            linked_object_type=data.get("linked_object_type", ""),
            linked_object_id=data.get("linked_object_id"),
        )
        EventBus.publish(
            FE.FINANCIAL_PROJECT_CREATE,
            company_id=company_id,
            payload={"financial_project_id": fp.id, "name": fp.name},
        )
        return fp


class CashAccountService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-03."""
        ca = CashAccount.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("CASH"),
            name=data["name"],
        )
        EventBus.publish(
            FE.CASH_ACCOUNT_CREATE,
            company_id=company_id,
            payload={"cash_account_id": ca.id, "name": ca.name},
        )
        return ca


class BankAccountService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-04."""
        ba = BankAccount.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("BANK"),
            bank_id=data.get("bank_id"),
            account_number=data["account_number"],
            currency_id=data.get("currency_id"),
        )
        EventBus.publish(
            FE.BANK_ACCOUNT_CREATE,
            company_id=company_id,
            payload={"bank_account_id": ba.id, "account_number": ba.account_number},
        )
        return ba


class ExchangeRateService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-05."""
        rate = ExchangeRate.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("RATE"),
            currency_id=data["currency_id"],
            rate_date=data["rate_date"],
            rate_value=data["rate_value"],
        )
        EventBus.publish(
            FE.EXCHANGE_RATE_CREATE,
            company_id=company_id,
            payload={
                "exchange_rate_id": rate.id,
                "currency_id": rate.currency_id,
                "rate_date": rate.rate_date.isoformat(),
            },
        )
        return rate