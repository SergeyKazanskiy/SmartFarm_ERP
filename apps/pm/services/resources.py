"""
Ресурсные потребности (OP-PM-20…23).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.pm.models import ResourceNeed
from apps.pm.services.helpers import gen_code


class ResourceNeedService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: ResourceNeed | None = None):
        """OP-PM-20 / OP-PM-21."""
        if instance is None:
            instance = ResourceNeed(
                company_id=company_id,
                code=data.get("code") or gen_code("RN"),
                sent_to_aps=False,
            )
        for field in (
            "task_id", "resource_type", "role_id", "skill_id",
            "quantity", "unit_id", "hours_per_day",
            "days_required", "priority",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.RESOURCE_NEED_SAVE,
            company_id=company_id,
            payload={
                "resource_need_id": instance.id,
                "task_id": instance.task_id,
                "resource_type": instance.resource_type,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def send_to_aps(*, company_id: int, resource_need_id: int):
        """OP-PM-22: пометить как отправленную в APS + событие для APS."""
        rn = ResourceNeed.objects.select_for_update().get(
            pk=resource_need_id, company_id=company_id,
        )
        if rn.sent_to_aps:
            return rn

        rn.sent_to_aps = True
        rn.sent_to_aps_at = timezone.now()
        rn.save(update_fields=["sent_to_aps", "sent_to_aps_at", "updated_at"])

        EventBus.publish(
            PM.RESOURCE_NEED_SEND_TO_APS,
            company_id=company_id,
            payload={
                "resource_need_id": rn.id,
                "task_id": rn.task_id,
                "resource_type": rn.resource_type,
                "role_id": rn.role_id,
                "skill_id": rn.skill_id,
                "quantity": float(rn.quantity),
                "hours_per_day": float(rn.hours_per_day) if rn.hours_per_day else None,
                "days_required": rn.days_required,
                "priority": rn.priority,
            },
        )
        return rn

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, resource_need_id: int):
        """OP-PM-23."""
        rn = ResourceNeed.objects.get(pk=resource_need_id, company_id=company_id)
        if rn.sent_to_aps:
            raise ValueError("Нельзя удалить потребность, уже отправленную в APS")
        rn.delete()

        EventBus.publish(
            PM.RESOURCE_NEED_SAVE,
            company_id=company_id,
            payload={
                "resource_need_id": resource_need_id,
                "action": "delete",
            },
        )