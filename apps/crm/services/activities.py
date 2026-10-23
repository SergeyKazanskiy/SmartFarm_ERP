"""
Активности (OP-CRM-13…14).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import CRMEvents as CRM

from apps.crm.models import Activity
from apps.crm.services.helpers import gen_code


class ActivityService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict, actor_employee_id: int | None = None):
        """OP-CRM-13: планирование активности."""
        if not data.get("lead_id") and not data.get("opportunity_id"):
            raise ValueError(_("Нужен хотя бы один из: lead_id, opportunity_id"))

        activity = Activity.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("ACT"),
            activity_type_id=data.get("activity_type_id"),
            lead_id=data.get("lead_id"),
            opportunity_id=data.get("opportunity_id"),
            employee_id=data.get("employee_id") or actor_employee_id,
            activity_date=data.get("activity_date") or timezone.now(),
            is_completed=False,
            subject=data.get("subject", ""),
        )

        EventBus.publish(
            CRM.ACTIVITY_CREATE,
            company_id=company_id,
            payload={
                "activity_id": activity.id,
                "lead_id": activity.lead_id,
                "opportunity_id": activity.opportunity_id,
                "activity_type_id": activity.activity_type_id,
            },
        )
        return activity

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, activity_id: int, result: str):
        """OP-CRM-14."""
        activity = Activity.objects.select_for_update().get(
            pk=activity_id, company_id=company_id,
        )
        if activity.is_completed:
            raise ValueError(_("Активность уже завершена"))

        activity.is_completed = True
        activity.result = result
        activity.save(update_fields=["is_completed", "result", "updated_at"])

        EventBus.publish(
            CRM.ACTIVITY_COMPLETE,
            company_id=company_id,
            payload={
                "activity_id": activity.id,
                "lead_id": activity.lead_id,
                "opportunity_id": activity.opportunity_id,
            },
        )
        return activity