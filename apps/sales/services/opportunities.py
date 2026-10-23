"""
Воронка продаж (OP-SALES-07…08).
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import Opportunity
from apps.sales.services.helpers import gen_code


# Автоподстановка probability_percent по стадии, как в SQL OP-SALES-08.
_STAGE_PROBABILITY = {
    "lead": 10,
    "negotiation": 30,
    "proposal": 60,
    "closed_won": 100,
    "closed_lost": 0,
}


class OpportunityService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict,
               actor_employee_id: int | None = None):
        """OP-SALES-07."""
        stage = data.get("stage") or "lead"
        opp = Opportunity.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("OPP"),
            customer_id=data["customer_id"],
            name=data["name"],
            stage=stage,
            expected_value=data.get("expected_value"),
            probability_percent=_STAGE_PROBABILITY.get(stage, 10),
            expected_close_date=data.get("expected_close_date"),
            created_by_employee_id=actor_employee_id,
        )

        EventBus.publish(
            SE.OPPORTUNITY_CREATE,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "customer_id": opp.customer_id,
                "stage": opp.stage,
                "expected_value": float(opp.expected_value) if opp.expected_value else None,
            },
        )
        return opp

    @staticmethod
    @transaction.atomic
    def update_stage(*, company_id: int, opportunity_id: int, new_stage: str):
        """OP-SALES-08. Автоподстановка probability по стадии."""
        if new_stage not in _STAGE_PROBABILITY:
            raise ValueError(f"Недопустимая стадия: {new_stage}")

        opp = Opportunity.objects.select_for_update().get(
            pk=opportunity_id, company_id=company_id,
        )
        old_stage = opp.stage
        opp.stage = new_stage
        opp.probability_percent = _STAGE_PROBABILITY[new_stage]
        opp.save(update_fields=["stage", "probability_percent", "updated_at"])

        EventBus.publish(
            SE.OPPORTUNITY_UPDATE_STAGE,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "old_stage": old_stage,
                "new_stage": new_stage,
            },
        )
        return opp