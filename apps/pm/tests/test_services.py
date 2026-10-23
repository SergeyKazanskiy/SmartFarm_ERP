import pytest

from core.event_bus import DomainEvent
from core.events import PMEvents as PM

from apps.pm.models import Project, Task
from apps.pm.services import (
    BudgetService, ProjectService, ResourceNeedService,
    RiskService, TaskService,
)


@pytest.mark.django_db
def test_project_save_publishes_event(company):
    p = ProjectService.save(
        company_id=company.id,
        data={"name": "X"},
        actor_employee_id=1,
    )
    event = DomainEvent.objects.filter(
        event_type=PM.PROJECT_SAVE, company=company,
    ).latest("id")
    assert event.payload["project_id"] == p.id


@pytest.mark.django_db
def test_project_status_transitions(company, project):
    ProjectService.update_status(
        company_id=company.id, project_id=project.id, new_status="active",
    )
    project.refresh_from_db()
    assert project.status == "active"
    assert project.actual_start_date is not None

    with pytest.raises(ValueError):
        ProjectService.complete(
            company_id=company.id, project_id=project.id,
        )
    ProjectService.update_status(
        company_id=company.id, project_id=project.id, new_status="on_hold",
    )
    with pytest.raises(ValueError):
        ProjectService.complete(
            company_id=company.id, project_id=project.id,
        )


@pytest.mark.django_db
def test_project_complete(company, project):
    ProjectService.update_status(
        company_id=company.id, project_id=project.id, new_status="active",
    )
    p = ProjectService.complete(
        company_id=company.id, project_id=project.id,
    )
    assert p.status == "completed"
    assert p.actual_end_date is not None


@pytest.mark.django_db
def test_task_status_and_complete(company, project):
    t = TaskService.save(
        company_id=company.id,
        data={"project_id": project.id, "name": "Задача"},
    )
    TaskService.update_status(
        company_id=company.id, task_id=t.id, new_status="in_progress",
    )
    t.refresh_from_db()
    assert t.status == "in_progress"
    assert t.actual_start_date is not None

    t = TaskService.complete(company_id=company.id, task_id=t.id)
    assert t.status == "completed"
    assert float(t.completion_percent) == 100.0


@pytest.mark.django_db
def test_risk_severity_computed(company, project):
    r = RiskService.save(
        company_id=company.id,
        data={
            "project_id": project.id,
            "name": "Риск",
            "probability": 40,
            "impact": 5,
        },
    )
    assert r.severity == 200


@pytest.mark.django_db
def test_resource_need_send_to_aps(company, project):
    t = TaskService.save(
        company_id=company.id,
        data={"project_id": project.id, "name": "Задача"},
    )
    rn = ResourceNeedService.save(
        company_id=company.id,
        data={
            "task_id": t.id,
            "resource_type": "employee",
            "quantity": 2,
        },
    )
    assert rn.sent_to_aps is False

    rn = ResourceNeedService.send_to_aps(
        company_id=company.id, resource_need_id=rn.id,
    )
    assert rn.sent_to_aps is True
    assert DomainEvent.objects.filter(
        event_type=PM.RESOURCE_NEED_SEND_TO_APS, company=company,
    ).exists()


@pytest.mark.django_db
def test_budget_approve(company, project):
    b = BudgetService.save(
        company_id=company.id,
        data={"project_id": project.id, "name": "B1", "total_planned_amount": 100000},
    )
    b = BudgetService.approve(
        company_id=company.id, budget_id=b.id, approver_employee_id=1,
    )
    assert b.status == "approved"