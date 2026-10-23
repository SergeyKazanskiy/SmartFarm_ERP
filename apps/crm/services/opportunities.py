"""
Сделки (OP-CRM-07…12).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import CRMEvents as CRM

from apps.crm.models import Opportunity
from apps.crm.services.helpers import gen_code


class OpportunityService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict, actor_employee_id: int | None = None):
        """OP-CRM-07: создание сделки (обычно из лида)."""
        opp = Opportunity.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("OPP"),
            lead_id=data.get("lead_id"),
            opportunity_stage_id=data.get("opportunity_stage_id"),
            responsible_employee_id=(
                data.get("responsible_employee_id") or actor_employee_id
            ),
            title=data.get("title", ""),
            amount=data.get("amount"),
            expected_close_date=data.get("expected_close_date"),
        )

        EventBus.publish(
            CRM.OPPORTUNITY_CREATE,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "code": opp.code,
                "lead_id": opp.lead_id,
                "amount": float(opp.amount) if opp.amount else None,
            },
        )
        return opp

    @staticmethod
    @transaction.atomic
    def update_stage(*, company_id: int, opportunity_id: int, stage_id: int):
        """OP-CRM-08. Только для открытой сделки (is_won IS NULL)."""
        opp = Opportunity.objects.select_for_update().get(
            pk=opportunity_id, company_id=company_id,
        )
        if opp.is_won is not None:
            raise ValueError(_("Сделка уже закрыта, смена стадии невозможна"))

        old = opp.opportunity_stage_id
        opp.opportunity_stage_id = stage_id
        opp.save(update_fields=["opportunity_stage", "updated_at"])

        EventBus.publish(
            CRM.OPPORTUNITY_UPDATE_STAGE,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "old_stage_id": old,
                "new_stage_id": stage_id,
            },
        )
        return opp

    @staticmethod
    @transaction.atomic
    def update_amount(*, company_id: int, opportunity_id: int,
                      amount, expected_close_date=None):
        """OP-CRM-09."""
        opp = Opportunity.objects.select_for_update().get(
            pk=opportunity_id, company_id=company_id,
        )
        if opp.is_won is not None:
            raise ValueError(_("Сделка уже закрыта"))

        opp.amount = amount
        if expected_close_date:
            opp.expected_close_date = expected_close_date
        opp.save(update_fields=["amount", "expected_close_date", "updated_at"])

        EventBus.publish(
            CRM.OPPORTUNITY_UPDATE_AMOUNT,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "amount": float(opp.amount) if opp.amount else None,
            },
        )
        return opp

    @staticmethod
    @transaction.atomic
    def assign(*, company_id: int, opportunity_id: int, employee_id: int):
        """OP-CRM-10."""
        opp = Opportunity.objects.select_for_update().get(
            pk=opportunity_id, company_id=company_id,
        )
        opp.responsible_employee_id = employee_id
        opp.save(update_fields=["responsible_employee_id", "updated_at"])

        EventBus.publish(
            CRM.OPPORTUNITY_ASSIGN,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "new_responsible_employee_id": employee_id,
            },
        )
        return opp

    @staticmethod
    @transaction.atomic
    def win(*, company_id: int, opportunity_id: int):
        """OP-CRM-11."""
        opp = Opportunity.objects.select_for_update().get(
            pk=opportunity_id, company_id=company_id,
        )
        if opp.is_won is not None:
            raise ValueError(_("Сделка уже закрыта"))

        opp.is_won = 1
        opp.save(update_fields=["is_won", "updated_at"])

        EventBus.publish(
            CRM.OPPORTUNITY_WIN,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "amount": float(opp.amount) if opp.amount else None,
            },
        )
        return opp

    @staticmethod
    @transaction.atomic
    def lose(*, company_id: int, opportunity_id: int, lost_reason: str):
        """OP-CRM-12."""
        opp = Opportunity.objects.select_for_update().get(
            pk=opportunity_id, company_id=company_id,
        )
        if opp.is_won is not None:
            raise ValueError(_("Сделка уже закрыта"))

        opp.is_won = 0
        opp.lost_reason = lost_reason
        opp.save(update_fields=["is_won", "lost_reason", "updated_at"])

        EventBus.publish(
            CRM.OPPORTUNITY_LOSE,
            company_id=company_id,
            payload={
                "opportunity_id": opp.id,
                "lost_reason": lost_reason,
            },
        )
        return opp