"""
Выполнение операций (OP-PROD-35…42).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import ProductionEvents as PRE

from apps.production.models import OperationExecution
from apps.production.services.helpers import (
    gen_code, has_failed_quality, validate_json_list,
)


class OperationExecutionService:

    @staticmethod
    @transaction.atomic
    def start(*, company_id: int, data: dict,
              actor_employee_id: int | None = None):
        """OP-PROD-35."""
        exec_ = OperationExecution.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("EXEC"),
            work_order_id=data["work_order_id"],
            operation_id=data["operation_id"],
            work_center_id=data.get("work_center_id"),
            performed_by_employee_id=(
                data.get("performed_by_employee_id") or actor_employee_id
            ),
            start_time=timezone.now(),
            status="in_progress",
        )
        EventBus.publish(
            PRE.EXECUTION_START,
            company_id=company_id,
            payload={
                "execution_id": exec_.id,
                "work_order_id": exec_.work_order_id,
                "operation_id": exec_.operation_id,
            },
        )
        return exec_

    @staticmethod
    @transaction.atomic
    def assign_employee(*, company_id: int, execution_id: int, employee_id: int):
        """OP-PROD-36."""
        ex = OperationExecution.objects.select_for_update().get(
            pk=execution_id, company_id=company_id,
        )
        ex.performed_by_employee_id = employee_id
        ex.save(update_fields=["performed_by_employee_id", "updated_at"])
        EventBus.publish(
            PRE.EXECUTION_ASSIGN_EMPLOYEE,
            company_id=company_id,
            payload={"execution_id": ex.id},
        )
        return ex

    @staticmethod
    @transaction.atomic
    def move_work_center(*, company_id: int, execution_id: int, work_center_id: int):
        """OP-PROD-37."""
        ex = OperationExecution.objects.select_for_update().get(
            pk=execution_id, company_id=company_id,
        )
        ex.work_center_id = work_center_id
        ex.save(update_fields=["work_center", "updated_at"])
        EventBus.publish(
            PRE.EXECUTION_MOVE_WORK_CENTER,
            company_id=company_id,
            payload={"execution_id": ex.id},
        )
        return ex

    @staticmethod
    @transaction.atomic
    def record_measurements(*, company_id: int, execution_id: int, measurements_json: list):
        """OP-PROD-38."""
        ex = OperationExecution.objects.select_for_update().get(
            pk=execution_id, company_id=company_id,
        )
        ex.measurements_json = validate_json_list(measurements_json, "measurements_json")
        ex.save(update_fields=["measurements_json", "updated_at"])
        EventBus.publish(
            PRE.EXECUTION_RECORD_MEASUREMENTS,
            company_id=company_id,
            payload={"execution_id": ex.id},
        )
        return ex

    @staticmethod
    @transaction.atomic
    def record_quality(*, company_id: int, execution_id: int, quality_results_json: list):
        """
        OP-PROD-39 + OP-PROD-41 (auto-rework).
        Если хоть один is_passed=false → автоматически переводим в rework.
        """
        ex = OperationExecution.objects.select_for_update().get(
            pk=execution_id, company_id=company_id,
        )
        ex.quality_results_json = validate_json_list(
            quality_results_json, "quality_results_json",
        )
        update_fields = ["quality_results_json", "updated_at"]

        # Автоматический перевод на доработку
        if has_failed_quality(ex.quality_results_json):
            if ex.status in ("in_progress", "completed"):
                ex.status = "rework"
                ex.end_time = None
                update_fields.extend(["status", "end_time"])

        ex.save(update_fields=update_fields)

        EventBus.publish(
            PRE.EXECUTION_RECORD_QUALITY,
            company_id=company_id,
            payload={
                "execution_id": ex.id,
                "status": ex.status,
                "has_failed_quality": has_failed_quality(ex.quality_results_json),
            },
        )
        return ex

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, execution_id: int):
        """OP-PROD-40."""
        ex = OperationExecution.objects.select_for_update().get(
            pk=execution_id, company_id=company_id,
        )
        if ex.status != "in_progress":
            raise ValueError(_("Завершить можно только in_progress"))

        ex.status = "completed"
        ex.end_time = timezone.now()
        ex.save(update_fields=["status", "end_time", "updated_at"])

        EventBus.publish(
            PRE.EXECUTION_COMPLETE,
            company_id=company_id,
            payload={
                "execution_id": ex.id,
                "work_order_id": ex.work_order_id,
                "operation_id": ex.operation_id,
            },
        )
        return ex

    @staticmethod
    @transaction.atomic
    def send_to_rework(*, company_id: int, execution_id: int, reason: str = ""):
        """OP-PROD-41 (ручной триггер)."""
        ex = OperationExecution.objects.select_for_update().get(
            pk=execution_id, company_id=company_id,
        )
        if ex.status != "completed":
            raise ValueError(_("На доработку можно вернуть только completed"))

        ex.status = "rework"
        ex.end_time = None
        ex.save(update_fields=["status", "end_time", "updated_at"])

        EventBus.publish(
            PRE.EXECUTION_SEND_TO_REWORK,
            company_id=company_id,
            payload={"execution_id": ex.id, "reason": reason},
        )
        return ex

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, execution_id: int):
        """OP-PROD-42."""
        ex = OperationExecution.objects.select_for_update().get(
            pk=execution_id, company_id=company_id,
        )
        if ex.status not in ("in_progress", "rework"):
            raise ValueError(_("Отменить можно только in_progress/rework"))

        ex.status = "cancelled"
        ex.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.EXECUTION_CANCEL,
            company_id=company_id,
            payload={"execution_id": ex.id},
        )
        return ex