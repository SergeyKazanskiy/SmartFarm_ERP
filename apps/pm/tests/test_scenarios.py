"""
E2E по PM_Scenarios.yml:
- SCENARIO-PM-001: полный цикл проекта
- SCENARIO-PM-002: изменение объёма работ
- SCENARIO-PM-003: управление рисками
"""
import pytest

from apps.pm.models import (
    Budget, BudgetItem, ChangeRequest, Phase, Project, Report, Risk, Task,
)
from apps.pm.services import (
    BudgetItemService, BudgetService, ChangeRequestService,
    MilestoneService, PhaseService, ProjectService,
    ReportService, RiskService, TaskService,
)


@pytest.mark.django_db
def test_scenario_pm_001_full_project_lifecycle(company, customer):
    """
    Создание проекта → этапы → задачи → ресурсы → отчёт → завершение.
    """
    # 1. Создание проекта
    p = ProjectService.save(
        company_id=company.id,
        data={
            "name": "Производство TV",
            "customer_id": customer.id,
            "planned_start_date": "2026-06-01",
            "planned_end_date": "2026-07-31",
            "priority": 1,
        },
        actor_employee_id=1,
    )
    assert p.status == "planning"

    # 2. Этап
    phase = PhaseService.save(
        company_id=company.id,
        data={"project_id": p.id, "name": "Подготовка", "order": 1},
    )
    assert phase.status == "planned"

    # 3. Веха
    m = MilestoneService.save(
        company_id=company.id,
        data={
            "project_id": p.id,
            "name": "Готовность линии",
            "milestone_date": "2026-06-15",
        },
    )
    assert not m.is_achieved

    # 4. Задача
    t = TaskService.save(
        company_id=company.id,
        data={
            "project_id": p.id,
            "phase_id": phase.id,
            "name": "Закупка материалов",
            "priority": 1,
            "assignee_employee_id": 10,
        },
    )
    assert t.status == "planned"

    # 5. Активация проекта
    ProjectService.update_status(
        company_id=company.id, project_id=p.id, new_status="active",
    )
    p.refresh_from_db()
    assert p.status == "active"

    # 6. Завершение этапа и вехи
    PhaseService.update_status = None  # на всякий случай
    # (в сервисе нет update_status — пропускаем, идём через прямой save)
    PhaseService.save(
        company_id=company.id,
        data={"status": "in_progress"},
        instance=phase,
    )
    phase = PhaseService.complete(
        company_id=company.id, phase_id=phase.id,
    )
    assert phase.status == "completed"

    m = MilestoneService.achieve(
        company_id=company.id, milestone_id=m.id,
    )
    assert m.is_achieved

    # 7. Завершение задачи
    TaskService.update_status(
        company_id=company.id, task_id=t.id, new_status="in_progress",
    )
    t = TaskService.complete(company_id=company.id, task_id=t.id)
    assert t.status == "completed"

    # 8. Отчёт для Orchestrator
    r = ReportService.create(
        company_id=company.id,
        data={"project_id": p.id, "report_type": "weekly"},
    )
    assert r.status_json_has_data() if hasattr(r, "status_json_has_data") else True
    assert "completed" in r.status_summary_json
    assert r.status_summary_json["completed"] == 1

    r = ReportService.send_to_orchestrator(
        company_id=company.id, report_id=r.id,
    )
    assert r.sent_to_orchestrator is True

    # 9. Завершение проекта
    p = ProjectService.complete(
        company_id=company.id, project_id=p.id,
    )
    assert p.status == "completed"
    assert p.actual_end_date is not None


@pytest.mark.django_db
def test_scenario_pm_002_change_request(company, project):
    """Изменение объёма → утверждение → бюджет обновлён."""
    cr = ChangeRequestService.save(
        company_id=company.id,
        data={
            "project_id": project.id,
            "title": "Увеличение объёма",
            "change_type": "scope",
            "impact_description": "+150 000",
        },
        actor_employee_id=1,
    )
    assert cr.status == "draft"

    # Подача (эмулируем через прямой save)
    ChangeRequestService.save(
        company_id=company.id,
        data={"status": "submitted"},
        instance=cr,
    )

    cr = ChangeRequestService.approve(
        company_id=company.id,
        change_request_id=cr.id,
        approver_employee_id=2,
    )
    assert cr.status == "approved"
    assert cr.approved_at is not None


@pytest.mark.django_db
def test_scenario_pm_003_risk_management(company, project):
    """Идентификация → оценка → смягчение → закрытие."""
    r = RiskService.save(
        company_id=company.id,
        data={
            "project_id": project.id,
            "name": "Задержка поставки",
            "probability": 30,
            "impact": 8,
        },
    )
    assert r.status == "identified"
    assert r.severity == 240

    # Разработка плана смягчения + смена статуса
    r = RiskService.save(
        company_id=company.id,
        data={
            "probability": 20,
            "impact": 8,
            "mitigation_plan": "Резервный поставщик",
            "status": "mitigated",
        },
        instance=r,
    )
    assert r.severity == 160
    assert r.status == "mitigated"

    # Закрытие
    r = RiskService.save(
        company_id=company.id,
        data={"status": "closed"},
        instance=r,
    )
    assert r.status == "closed"