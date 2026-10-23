"""
Демо-команда: загружает PM_test_data.json.

Использование:
    python manage.py demo_pm --company=1
    python manage.py demo_pm --company=1 --file=apps/pm/workflow/PM_test_data.json
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.cp.models import Counterparty
from apps.pm.models import (
    Budget, BudgetItem, ChangeRequest, Milestone, Phase, Project,
    Report, ResourceNeed, Risk, StatusHistory, Task, TaskDependency,
)


class Command(BaseCommand):
    help = "Загружает тестовые данные PM и публикует события"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/pm/workflow/PM_test_data.json",
        )
        parser.add_argument("--emit-events", action="store_true", default=True)

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(pk=options["company"])
        except Company.DoesNotExist:
            raise CommandError(f"Company {options['company']} not found")

        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tables = data.get("tables", {})
        counters = {}

        with transaction.atomic():
            # Порядок важен: сначала проекты, потом дочерние
            counters["project"] = self._load_projects(
                company, tables.get("pm_project", []),
            )
            counters["phase"] = self._load_phases(
                company, tables.get("pm_phase", []),
            )
            counters["milestone"] = self._load_milestones(
                company, tables.get("pm_milestone", []),
            )
            counters["task"] = self._load_tasks(
                company, tables.get("pm_task", []),
            )
            counters["task_dependency"] = self._load_task_dependencies(
                company, tables.get("pm_task_dependency", []),
            )
            counters["resource_need"] = self._load_resource_needs(
                company, tables.get("pm_resource_need", []),
            )
            counters["budget"] = self._load_budgets(
                company, tables.get("pm_budget", []),
            )
            counters["budget_item"] = self._load_budget_items(
                company, tables.get("pm_budget_item", []),
            )
            counters["risk"] = self._load_risks(
                company, tables.get("pm_risk", []),
            )
            counters["change_request"] = self._load_change_requests(
                company, tables.get("pm_change_request", []),
            )
            counters["status_history"] = self._load_status_history(
                company, tables.get("pm_status_history", []),
            )
            counters["report"] = self._load_reports(
                company, tables.get("pm_report", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные PM загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # ------------------------------------------------------------------
    # Загрузчики
    # ------------------------------------------------------------------

    def _load_projects(self, company, rows) -> int:
        n = 0
        for r in rows:
            Project.objects.update_or_create(
                company=company, code=r["project_id"],
                defaults={
                    "name": r["project_name"],
                    "project_code": r.get("project_code", ""),
                    "description": r.get("description", ""),
                    "orchestrator_id": r.get("orchestrator_id") or "",
                    "customer_id": self._resolve_cp(r.get("customer_id"), company),
                    "project_manager_employee_id": _parse_emp_id(
                        r.get("project_manager_employee_id")
                    ),
                    "planned_start_date": r.get("planned_start_date"),
                    "planned_end_date": r.get("planned_end_date"),
                    "actual_start_date": r.get("actual_start_date"),
                    "actual_end_date": r.get("actual_end_date"),
                    "status": r.get("status_id", "planning"),
                    "priority": r.get("priority"),
                    "created_by_employee_id": _parse_emp_id(
                        r.get("created_by_employee_id")
                    ),
                },
            )
            n += 1
        return n

    def _load_phases(self, company, rows) -> int:
        n = 0
        # Первый проход: без parent
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            Phase.objects.update_or_create(
                company=company, code=r["phase_id"],
                defaults={
                    "project": project,
                    "name": r["phase_name"],
                    "order": r.get("phase_order", 0),
                    "planned_start_date": r.get("planned_start_date"),
                    "planned_end_date": r.get("planned_end_date"),
                    "actual_start_date": r.get("actual_start_date"),
                    "actual_end_date": r.get("actual_end_date"),
                    "status": r.get("status_id", "planned"),
                    "completion_percent": r.get("completion_percent", 0),
                },
            )
            n += 1
        # Второй проход: parent
        for r in rows:
            if r.get("parent_phase_id"):
                parent = Phase.objects.filter(
                    company=company, code=r["parent_phase_id"],
                ).first()
                if parent:
                    Phase.objects.filter(
                        company=company, code=r["phase_id"],
                    ).update(parent=parent)
        return n

    def _load_milestones(self, company, rows) -> int:
        n = 0
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            Milestone.objects.update_or_create(
                company=company, code=r["milestone_id"],
                defaults={
                    "project": project,
                    "name": r["milestone_name"],
                    "milestone_date": r["milestone_date"],
                    "is_achieved": r.get("is_achieved", False),
                    "achieved_date": r.get("achieved_date"),
                    "description": r.get("description", ""),
                },
            )
            n += 1
        return n

    def _load_tasks(self, company, rows) -> int:
        n = 0
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            phase = (
                Phase.objects.get(company=company, code=r["phase_id"])
                if r.get("phase_id") else None
            )
            parent = (
                Task.objects.filter(company=company, code=r["parent_task_id"]).first()
                if r.get("parent_task_id") else None
            )
            Task.objects.update_or_create(
                company=company, code=r["task_id"],
                defaults={
                    "project": project,
                    "phase": phase,
                    "parent": parent,
                    "name": r["task_name"],
                    "description": r.get("description", ""),
                    "planned_start_date": r.get("planned_start_date"),
                    "planned_end_date": r.get("planned_end_date"),
                    "actual_start_date": r.get("actual_start_date"),
                    "actual_end_date": r.get("actual_end_date"),
                    "status": r.get("status_id", "planned"),
                    "completion_percent": r.get("completion_percent", 0),
                    "priority": r.get("priority"),
                    "assignee_employee_id": _parse_emp_id(
                        r.get("assignee_employee_id")
                    ),
                },
            )
            n += 1
        return n

    def _load_task_dependencies(self, company, rows) -> int:
        n = 0
        for r in rows:
            pred = Task.objects.get(company=company, code=r["predecessor_task_id"])
            succ = Task.objects.get(company=company, code=r["successor_task_id"])
            TaskDependency.objects.update_or_create(
                company=company,
                predecessor=pred,
                successor=succ,
                defaults={
                    "code": r["dependency_id"],
                    "dependency_type": r.get("dependency_type", "FS"),
                    "lag_days": r.get("lag_days", 0),
                },
            )
            n += 1
        return n

    def _load_resource_needs(self, company, rows) -> int:
        n = 0
        for r in rows:
            task = Task.objects.get(company=company, code=r["task_id"])
            ResourceNeed.objects.update_or_create(
                company=company, code=r["resource_need_id"],
                defaults={
                    "task": task,
                    "resource_type": r["resource_type"],
                    "role_id": _parse_emp_id(r.get("role_id")),
                    "skill_id": _parse_emp_id(r.get("skill_id")),
                    "quantity": r["quantity"],
                    "unit_id": _parse_emp_id(r.get("unit_id")),
                    "hours_per_day": r.get("hours_per_day"),
                    "days_required": r.get("days_required"),
                    "priority": r.get("priority"),
                    "sent_to_aps": r.get("sent_to_aps", False),
                    "sent_to_aps_at": r.get("sent_to_aps_at"),
                },
            )
            n += 1
        return n

    def _load_budgets(self, company, rows) -> int:
        n = 0
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            Budget.objects.update_or_create(
                company=company, code=r["budget_id"],
                defaults={
                    "project": project,
                    "name": r.get("budget_name", ""),
                    "total_planned_amount": r.get("total_planned_amount"),
                    "total_actual_amount": r.get("total_actual_amount"),
                    "currency_id": _parse_emp_id(r.get("currency_id")),
                    "status": r.get("status_id", "draft"),
                    "approved_by_employee_id": _parse_emp_id(
                        r.get("approved_by_employee_id")
                    ),
                    "approved_at": r.get("approved_at"),
                },
            )
            n += 1
        return n

    def _load_budget_items(self, company, rows) -> int:
        n = 0
        for r in rows:
            budget = Budget.objects.get(company=company, code=r["budget_id"])
            BudgetItem.objects.update_or_create(
                company=company, code=r["budget_item_id"],
                defaults={
                    "budget": budget,
                    "category": r["category"],
                    "planned_amount": r["planned_amount"],
                    "actual_amount": r.get("actual_amount"),
                    "description": r.get("description", ""),
                },
            )
            n += 1
        return n

    def _load_risks(self, company, rows) -> int:
        n = 0
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            Risk.objects.update_or_create(
                company=company, code=r["risk_id"],
                defaults={
                    "project": project,
                    "name": r["risk_name"],
                    "description": r.get("description", ""),
                    "probability": r.get("probability"),
                    "impact": r.get("impact"),
                    "severity": r.get("severity"),
                    "mitigation_plan": r.get("mitigation_plan", ""),
                    "status": r.get("status_id", "identified"),
                    "owner_employee_id": _parse_emp_id(r.get("owner_employee_id")),
                },
            )
            n += 1
        return n

    def _load_change_requests(self, company, rows) -> int:
        n = 0
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            ChangeRequest.objects.update_or_create(
                company=company, code=r["change_request_id"],
                defaults={
                    "project": project,
                    "title": r["title"],
                    "description": r.get("description", ""),
                    "change_type": r["change_type"],
                    "impact_description": r.get("impact_description", ""),
                    "status": r.get("status_id", "draft"),
                    "requested_by_employee_id": _parse_emp_id(
                        r.get("requested_by_employee_id")
                    ),
                    "approved_by_employee_id": _parse_emp_id(
                        r.get("approved_by_employee_id")
                    ),
                    "requested_at": r.get("requested_at"),
                    "approved_at": r.get("approved_at"),
                },
            )
            n += 1
        return n

    def _load_status_history(self, company, rows) -> int:
        n = 0
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            StatusHistory.objects.update_or_create(
                company=company,
                project=project,
                changed_at=r["changed_at"],
                defaults={
                    "status_from": r.get("status_from", ""),
                    "status_to": r["status_to"],
                    "changed_by_employee_id": _parse_emp_id(
                        r.get("changed_by_employee_id")
                    ),
                    "comment": r.get("comment", ""),
                },
            )
            n += 1
        return n

    def _load_reports(self, company, rows) -> int:
        n = 0
        for r in rows:
            project = Project.objects.get(company=company, code=r["project_id"])
            Report.objects.update_or_create(
                company=company, code=r["report_id"],
                defaults={
                    "project": project,
                    "report_date": r["report_date"],
                    "report_type": r["report_type"],
                    "summary": r.get("summary", ""),
                    "status_summary_json": r.get("status_summary_json") or {},
                    "budget_summary_json": r.get("budget_summary_json") or {},
                    "schedule_summary_json": r.get("schedule_summary_json") or {},
                    "risks_summary_json": r.get("risks_summary_json") or {},
                    "sent_to_orchestrator": r.get("sent_to_orchestrator", False),
                    "sent_to_orchestrator_at": r.get("sent_to_orchestrator_at"),
                },
            )
            n += 1
        return n

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    def _resolve_cp(self, code: str | None, company) -> int | None:
        """'CP-001' → Counterparty.id (или None, если CP не загружен)."""
        if not code:
            return None
        cp = Counterparty.objects.filter(company=company, code=code).first()
        return cp.id if cp else None

    def _emit_events(self, company) -> None:
        for p in Project.objects.filter(company=company):
            EventBus.publish(
                PM.PROJECT_SAVE,
                company_id=company.id,
                payload={
                    "project_id": p.id,
                    "code": p.code,
                    "status": p.status,
                    "customer_id": p.customer_id,
                },
            )
        for t in Task.objects.filter(company=company):
            EventBus.publish(
                PM.TASK_SAVE,
                company_id=company.id,
                payload={
                    "task_id": t.id,
                    "project_id": t.project_id,
                    "phase_id": t.phase_id,
                },
            )


def _parse_emp_id(value) -> int | None:
    """'EMP-010' → 10; 'POS-010' → 10; 'UNIT-001' → 1; 'CUR-001' → 1."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        for prefix in ("EMP-", "POS-", "UNIT-", "CUR-", "MAT-", "NP-", "DOC-"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None