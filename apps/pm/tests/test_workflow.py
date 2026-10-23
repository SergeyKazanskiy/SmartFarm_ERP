from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import PMEvents as PM
from core.workflow_loader import WorkflowLoader

from apps.pm.models import Project
from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/pm/workflow")


@pytest.mark.django_db
def test_workflow_loads_and_resolves_events(company):
    loader = WorkflowLoader(
        company_id=company.id,
        module="PM",
        business_roles_path=WORKFLOW_DIR / "PM_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "PM_Process_Workflow.yml")

    # 31 задача в PM_Process_Workflow.yml
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 31

    d = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-PM-01-01",
    )
    assert PM.PROJECT_SAVE in d.on_events


@pytest.mark.django_db
def test_task_created_on_project_save(company):
    loader = WorkflowLoader(
        company_id=company.id, module="PM",
        business_roles_path=WORKFLOW_DIR / "PM_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "PM_Process_Workflow.yml")

    p = Project.objects.create(
        company=company, code="PROJ-X", name="X",
    )
    EventBus.publish(
        PM.PROJECT_SAVE,
        company_id=company.id,
        payload={"project_id": p.id, "code": p.code, "status": p.status},
    )
    call_command("process_events", "--once")

    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-PM-01-01",
    ).exists()