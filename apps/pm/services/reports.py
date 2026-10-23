"""
История статусов (OP-PM-33) и отчёты (OP-PM-34…35).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone

from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.pm.models import (
    Budget, BudgetItem, Project, Report, Risk, StatusHistory, Task,
)
from apps.pm.services.helpers import gen_code


class StatusHistoryService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict,
               actor_employee_id: int | None = None):
        """OP-PM-33."""
        record = StatusHistory.objects.create(
            company_id=company_id,
            project_id=data["project_id"],
            status_from=data.get("status_from", ""),
            status_to=data["status_to"],
            changed_by_employee_id=actor_employee_id,
            changed_at=timezone.now(),
            comment=data.get("comment", ""),
        )
        EventBus.publish(
            PM.STATUS_HISTORY_CREATE,
            company_id=company_id,
            payload={
                "history_id": record.id,
                "project_id": record.project_id,
                "status_from": record.status_from,
                "status_to": record.status_to,
            },
        )
        return record


class ReportService:
    """
    OP-PM-34: создание отчёта с автоматическим заполнением
    4 JSON-блоков (status/budget/schedule/risks) по актуальным данным проекта.
    """

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        project_id = data["project_id"]
        project = Project.objects.get(pk=project_id, company_id=company_id)

        # status_summary: количество задач по статусам
        status_qs = Task.objects.filter(
            company_id=company_id, project_id=project_id,
        ).values("status").annotate(cnt=Count("id"))
        status_summary = {row["status"]: row["cnt"] for row in status_qs}

        # budget_summary: плановые/фактические суммы из бюджета
        budget = Budget.objects.filter(
            company_id=company_id, project_id=project_id,
        ).first()
        if budget:
            planned = budget.total_planned_amount or Decimal("0")
            actual = (
                BudgetItem.objects.filter(
                    company_id=company_id, budget=budget,
                    actual_amount__isnull=False,
                ).aggregate(s=Sum("actual_amount"))["s"]
                or Decimal("0")
            )
            budget_summary = {
                "planned": float(planned),
                "actual": float(actual),
                "variance": float(planned - actual),
            }
        else:
            budget_summary = {}

        # schedule_summary: on_track / days_delay
        today = timezone.now().date()
        overdue_tasks = Task.objects.filter(
            company_id=company_id, project_id=project_id,
            status__in=["planned", "in_progress"],
            planned_end_date__lt=today,
        ).count()
        days_delay = 0
        if overdue_tasks:
            earliest_overdue = Task.objects.filter(
                company_id=company_id, project_id=project_id,
                status__in=["planned", "in_progress"],
                planned_end_date__lt=today,
            ).order_by("planned_end_date").first()
            days_delay = (today - earliest_overdue.planned_end_date).days

        schedule_summary = {
            "on_track": overdue_tasks == 0,
            "days_delay": days_delay,
        }

        # risks_summary: активные / закрытые
        risks_qs = Risk.objects.filter(
            company_id=company_id, project_id=project_id,
        ).aggregate(
            active=Count("id", filter=~Q(status="closed")),
            closed=Count("id", filter=Q(status="closed")),
        )
        risks_summary = {
            "active": risks_qs["active"] or 0,
            "closed": risks_qs["closed"] or 0,
        }

        report = Report.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("REP"),
            project=project,
            report_date=timezone.now(),
            report_type=data["report_type"],
            summary=data.get("summary", ""),
            status_summary_json=status_summary,
            budget_summary_json=budget_summary,
            schedule_summary_json=schedule_summary,
            risks_summary_json=risks_summary,
            sent_to_orchestrator=False,
        )

        EventBus.publish(
            PM.REPORT_CREATE,
            company_id=company_id,
            payload={
                "report_id": report.id,
                "project_id": project_id,
                "report_type": report.report_type,
            },
        )
        return report

    @staticmethod
    @transaction.atomic
    def send_to_orchestrator(*, company_id: int, report_id: int):
        """OP-PM-35."""
        report = Report.objects.select_for_update().get(
            pk=report_id, company_id=company_id,
        )
        if report.sent_to_orchestrator:
            return report

        report.sent_to_orchestrator = True
        report.sent_to_orchestrator_at = timezone.now()
        report.save(update_fields=[
            "sent_to_orchestrator", "sent_to_orchestrator_at", "updated_at",
        ])

        EventBus.publish(
            PM.REPORT_SEND_TO_ORCHESTRATOR,
            company_id=company_id,
            payload={
                "report_id": report.id,
                "project_id": report.project_id,
            },
        )
        return report