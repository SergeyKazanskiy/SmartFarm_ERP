"""
Финансовые периоды (OP-FIN-19…20) и показатели (OP-FIN-21).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import FinanceEvents as FE

from apps.finance.models import FinancialIndicator, FinancialPeriod
from apps.finance.services.helpers import gen_code


class FinancialPeriodService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-19."""
        period = FinancialPeriod.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("PER"),
            name=data["name"],
            date_from=data["date_from"],
            date_to=data["date_to"],
            is_closed=False,
        )
        EventBus.publish(
            FE.FINANCIAL_PERIOD_CREATE,
            company_id=company_id,
            payload={"period_id": period.id, "name": period.name},
        )
        return period

    @staticmethod
    @transaction.atomic
    def close(*, company_id: int, period_id: int):
        """OP-FIN-20."""
        period = FinancialPeriod.objects.select_for_update().get(
            pk=period_id, company_id=company_id,
        )
        if period.is_closed:
            return period
        period.is_closed = True
        period.save(update_fields=["is_closed", "updated_at"])

        EventBus.publish(
            FE.FINANCIAL_PERIOD_CLOSE,
            company_id=company_id,
            payload={"period_id": period.id, "date_to": period.date_to.isoformat()},
        )
        return period


class FinancialIndicatorService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-21."""
        indicator = FinancialIndicator.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("FI"),
            financial_project_id=data.get("financial_project_id"),
            period_id=data.get("period_id"),
            indicator_code=data["indicator_code"],
            indicator_value=data["indicator_value"],
        )
        EventBus.publish(
            FE.FINANCIAL_INDICATOR_CREATE,
            company_id=company_id,
            payload={
                "indicator_id": indicator.id,
                "indicator_code": indicator.indicator_code,
                "value": float(indicator.indicator_value) if indicator.indicator_value else None,
            },
        )
        return indicator