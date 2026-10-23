"""
Задачи (OP-PM-13…17) и зависимости (OP-PM-18…19).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.pm.models import Task, TaskDependency
from apps.pm.services.helpers import gen_code


class TaskService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Task | None = None):
        """OP-PM-13 / OP-PM-14."""
        if instance is None:
            instance = Task(
                company_id=company_id,
                code=data.get("code") or gen_code("PTASK"),
                status="planned",
            )
        for field in (
            "project_id", "phase_id", "parent_id",
            "name", "description",
            "planned_start_date", "planned_end_date",
            "priority", "assignee_employee_id",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.TASK_SAVE,
            company_id=company_id,
            payload={
                "task_id": instance.id,
                "project_id": instance.project_id,
                "phase_id": instance.phase_id,
                "assignee_employee_id": instance.assignee_employee_id,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def update_status(*, company_id: int, task_id: int,
                      new_status: str, completion_percent: float | None = None):
        """OP-PM-15."""
        task = Task.objects.select_for_update().get(
            pk=task_id, company_id=company_id,
        )
        if new_status not in dict(Task.STATUS_CHOICES):
            raise ValueError(_("Недопустимый статус: %s") % new_status)

        old = task.status
        task.status = new_status
        update_fields = ["status", "updated_at"]

        if completion_percent is not None:
            task.completion_percent = completion_percent
            update_fields.append("completion_percent")

        # 'in_progress' → фиксируем actual_start, если ещё нет
        if new_status == "in_progress" and not task.actual_start_date:
            task.actual_start_date = timezone.now().date()
            update_fields.append("actual_start_date")

        task.save(update_fields=update_fields)

        EventBus.publish(
            PM.TASK_UPDATE_STATUS,
            company_id=company_id,
            payload={
                "task_id": task.id,
                "project_id": task.project_id,
                "old_status": old,
                "new_status": new_status,
            },
        )
        return task

    @staticmethod
    @transaction.atomic
    def assign(*, company_id: int, task_id: int, employee_id: int):
        """OP-PM-16."""
        task = Task.objects.select_for_update().get(
            pk=task_id, company_id=company_id,
        )
        old = task.assignee_employee_id
        task.assignee_employee_id = employee_id
        task.save(update_fields=["assignee_employee_id", "updated_at"])

        EventBus.publish(
            PM.TASK_ASSIGN,
            company_id=company_id,
            payload={
                "task_id": task.id,
                "old_assignee_employee_id": old,
                "new_assignee_employee_id": employee_id,
            },
        )
        return task

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, task_id: int):
        """OP-PM-17."""
        task = Task.objects.select_for_update().get(
            pk=task_id, company_id=company_id,
        )
        if task.status != "in_progress":
            raise ValueError(_("Завершить можно только задачу в статусе in_progress"))

        task.status = "completed"
        task.completion_percent = 100
        task.actual_end_date = timezone.now().date()
        task.save(update_fields=[
            "status", "completion_percent", "actual_end_date", "updated_at",
        ])

        EventBus.publish(
            PM.TASK_COMPLETE,
            company_id=company_id,
            payload={
                "task_id": task.id,
                "project_id": task.project_id,
                "assignee_employee_id": task.assignee_employee_id,
            },
        )
        return task


class TaskDependencyService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict):
        """OP-PM-18: создание или обновление зависимости."""
        if data["predecessor_task_id"] == data["successor_task_id"]:
            raise ValueError(_("Задача не может зависеть от самой себя"))

        dep, _ = TaskDependency.objects.update_or_create(
            company_id=company_id,
            predecessor_id=data["predecessor_task_id"],
            successor_id=data["successor_task_id"],
            defaults={
                "code": data.get("code") or gen_code("DEP"),
                "dependency_type": data.get("dependency_type", "FS"),
                "lag_days": data.get("lag_days", 0),
            },
        )

        EventBus.publish(
            PM.TASK_DEPENDENCY_SAVE,
            company_id=company_id,
            payload={
                "dependency_id": dep.id,
                "predecessor_task_id": dep.predecessor_id,
                "successor_task_id": dep.successor_id,
                "action": "save",
            },
        )
        return dep

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, dependency_id: int):
        """OP-PM-19."""
        dep = TaskDependency.objects.get(pk=dependency_id, company_id=company_id)
        payload = {
            "dependency_id": dep.id,
            "predecessor_task_id": dep.predecessor_id,
            "successor_task_id": dep.successor_id,
            "action": "delete",
        }
        dep.delete()

        EventBus.publish(
            PM.TASK_DEPENDENCY_SAVE,
            company_id=company_id,
            payload=payload,
        )