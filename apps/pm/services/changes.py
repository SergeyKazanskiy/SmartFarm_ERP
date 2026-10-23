"""
Риски (OP-PM-29…30) и запросы на изменение (OP-PM-31…32).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.pm.models import ChangeRequest, Risk
from apps.pm.services.helpers import gen_code


class RiskService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Risk | None = None):
        """OP-PM-29 / OP-PM-30."""
        if instance is None:
            instance = Risk(
                company_id=company_id,
                code=data.get("code") or gen_code("RISK"),
                status="identified",
            )
        for field in (
            "project_id", "name", "description",
            "probability", "impact", "mitigation_plan",
            "status", "owner_employee_id",
        ):
            if field in data:
                setattr(instance, field, data[field])

        # severity = probability × impact (пересчитывается автоматически)
        if instance.probability is not None and instance.impact is not None:
            instance.severity = instance.probability * instance.impact

        instance.save()

        EventBus.publish(
            PM.RISK_SAVE,
            company_id=company_id,
            payload={
                "risk_id": instance.id,
                "project_id": instance.project_id,
                "severity": instance.severity,
                "status": instance.status,
            },
        )
        return instance


class ChangeRequestService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: ChangeRequest | None = None,
             actor_employee_id: int | None = None):
        """OP-PM-31 / OP-PM-32 (утверждение — отдельный метод)."""
        if instance is None:
            instance = ChangeRequest(
                company_id=company_id,
                code=data.get("code") or gen_code("CR"),
                status="draft",
                requested_by_employee_id=actor_employee_id,
                requested_at=timezone.now(),
            )
        for field in (
            "project_id", "title", "description",
            "change_type", "impact_description", "status",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.CHANGE_REQUEST_SAVE,
            company_id=company_id,
            payload={
                "change_request_id": instance.id,
                "project_id": instance.project_id,
                "status": instance.status,
                "change_type": instance.change_type,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def approve(*, company_id: int, change_request_id: int,
                approver_employee_id: int):
        """OP-PM-32: утверждение изменения."""
        cr = ChangeRequest.objects.select_for_update().get(
            pk=change_request_id, company_id=company_id,
        )
        if cr.status != "submitted":
            raise ValueError(_("Утвердить можно только поданный запрос"))

        cr.status = "approved"
        cr.approved_by_employee_id = approver_employee_id
        cr.approved_at = timezone.now()
        cr.save(update_fields=[
            "status", "approved_by_employee_id", "approved_at", "updated_at",
        ])

        EventBus.publish(
            PM.CHANGE_REQUEST_SAVE,
            company_id=company_id,
            payload={
                "change_request_id": cr.id,
                "project_id": cr.project_id,
                "status": cr.status,
                "change_type": cr.change_type,
                "action": "approve",
            },
        )
        return cr