"""
Этапы (OP-PM-08…10) и вехи (OP-PM-11…12).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.pm.models import Milestone, Phase
from apps.pm.services.helpers import gen_code


class PhaseService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Phase | None = None):
        """OP-PM-08 / OP-PM-09."""
        if instance is None:
            instance = Phase(
                company_id=company_id,
                code=data.get("code") or gen_code("PHASE"),
                status="planned",
            )
        for field in (
            "project_id", "parent_id", "name", "order",
            "planned_start_date", "planned_end_date",
            "status", "completion_percent",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.PHASE_SAVE,
            company_id=company_id,
            payload={
                "phase_id": instance.id,
                "project_id": instance.project_id,
                "status": instance.status,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, phase_id: int):
        """OP-PM-10."""
        phase = Phase.objects.select_for_update().get(
            pk=phase_id, company_id=company_id,
        )
        if phase.status != "in_progress":
            raise ValueError("Завершить можно только этап в статусе in_progress")

        phase.status = "completed"
        phase.completion_percent = 100
        phase.actual_end_date = timezone.now().date()
        phase.save(update_fields=[
            "status", "completion_percent", "actual_end_date", "updated_at",
        ])

        EventBus.publish(
            PM.PHASE_COMPLETE,
            company_id=company_id,
            payload={"phase_id": phase.id, "project_id": phase.project_id},
        )
        return phase


class MilestoneService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Milestone | None = None):
        """OP-PM-11: создание вехи."""
        if instance is None:
            instance = Milestone(
                company_id=company_id,
                code=data.get("code") or gen_code("MIL"),
                is_achieved=False,
            )
        for field in (
            "project_id", "name", "milestone_date", "description",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.MILESTONE_SAVE,
            company_id=company_id,
            payload={
                "milestone_id": instance.id,
                "project_id": instance.project_id,
                "is_achieved": instance.is_achieved,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def achieve(*, company_id: int, milestone_id: int):
        """OP-PM-12: достижение вехи."""
        milestone = Milestone.objects.select_for_update().get(
            pk=milestone_id, company_id=company_id,
        )
        if milestone.is_achieved:
            return milestone

        milestone.is_achieved = True
        milestone.achieved_date = timezone.now().date()
        milestone.save(update_fields=["is_achieved", "achieved_date", "updated_at"])

        EventBus.publish(
            PM.MILESTONE_SAVE,
            company_id=company_id,
            payload={
                "milestone_id": milestone.id,
                "project_id": milestone.project_id,
                "is_achieved": True,
            },
        )
        return milestone