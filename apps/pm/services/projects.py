"""
Проекты (OP-PM-01…06).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.pm.models import Project
from apps.pm.services.helpers import gen_code


class ProjectService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: Project | None = None,
             actor_employee_id: int | None = None):
        """OP-PM-01 / OP-PM-02: создание или обновление проекта."""
        if instance is None:
            instance = Project(
                company_id=company_id,
                code=data.get("code") or gen_code("PROJ"),
                status="planning",
                created_by_employee_id=actor_employee_id,
            )
        for field in (
            "name", "project_code", "description",
            "orchestrator_id", "customer_id", "project_manager_employee_id",
            "planned_start_date", "planned_end_date",
            "priority",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.PROJECT_SAVE,
            company_id=company_id,
            payload={
                "project_id": instance.id,
                "code": instance.code,
                "status": instance.status,
                "customer_id": instance.customer_id,
                "project_manager_employee_id": instance.project_manager_employee_id,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def update_status(*, company_id: int, project_id: int, new_status: str):
        """OP-PM-03."""
        project = Project.objects.select_for_update().get(
            pk=project_id, company_id=company_id,
        )
        if new_status not in dict(Project.STATUS_CHOICES):
            raise ValueError(_("Недопустимый статус: %s") % new_status)

        old = project.status
        project.status = new_status
        update_fields = ["status", "updated_at"]

        # Переход в 'active' — фиксируем фактическую дату начала (если ещё нет)
        if new_status == "active" and not project.actual_start_date:
            from django.utils import timezone
            project.actual_start_date = timezone.now().date()
            update_fields.append("actual_start_date")

        project.save(update_fields=update_fields)

        EventBus.publish(
            PM.PROJECT_UPDATE_STATUS,
            company_id=company_id,
            payload={
                "project_id": project.id,
                "old_status": old,
                "new_status": new_status,
            },
        )
        return project

    @staticmethod
    @transaction.atomic
    def assign_manager(*, company_id: int, project_id: int, employee_id: int):
        """OP-PM-04."""
        project = Project.objects.select_for_update().get(
            pk=project_id, company_id=company_id,
        )
        old = project.project_manager_employee_id
        project.project_manager_employee_id = employee_id
        project.save(update_fields=["project_manager_employee_id", "updated_at"])

        EventBus.publish(
            PM.PROJECT_ASSIGN_MANAGER,
            company_id=company_id,
            payload={
                "project_id": project.id,
                "old_manager_employee_id": old,
                "new_manager_employee_id": employee_id,
            },
        )
        return project

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, project_id: int):
        """OP-PM-05."""
        project = Project.objects.select_for_update().get(
            pk=project_id, company_id=company_id,
        )
        if project.status != "active":
            raise ValueError(_("Завершить можно только активный проект"))

        from django.utils import timezone
        project.status = "completed"
        project.actual_end_date = timezone.now().date()
        project.save(update_fields=["status", "actual_end_date", "updated_at"])

        EventBus.publish(
            PM.PROJECT_COMPLETE,
            company_id=company_id,
            payload={
                "project_id": project.id,
                "customer_id": project.customer_id,
            },
        )
        return project

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, project_id: int):
        """OP-PM-06."""
        project = Project.objects.select_for_update().get(
            pk=project_id, company_id=company_id,
        )
        if project.status not in ("planning", "active"):
            raise ValueError(_("Отменить можно только проект в статусе planning или active"))

        project.status = "cancelled"
        project.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PM.PROJECT_CANCEL,
            company_id=company_id,
            payload={"project_id": project.id},
        )
        return project