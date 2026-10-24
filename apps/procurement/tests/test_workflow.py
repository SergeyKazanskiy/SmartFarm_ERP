from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import ProcurementEvents as PE
from core.workflow_loader import WorkflowLoader

from apps.procurement.models import Requisition
from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/procurement/workflow")


@pytest.mark.django_db
def test_workflow_loads(company):
    loader = WorkflowLoader(
        company_id=company.id, module="PROCUREMENT",
        business_roles_path=WORKFLOW_DIR / "PROCUREMENT_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "PROCUREMENT_Process_Workflow.yml")

    # 13 задач в PROCUREMENT_Process_Workflow.yml
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 13

    d = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-PROC-02-01",
    )
    assert PE.REQUISITION_CREATE in d.on_events


@pytest.mark.django_db
def test_task_created_on_requisition_create(company):
    loader = WorkflowLoader(
        company_id=company.id, module="PROCUREMENT",
        business_roles_path=WORKFLOW_DIR / "PROCUREMENT_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "PROCUREMENT_Process_Workflow.yml")

    req = Requisition.objects.create(
        company=company, code="REQ-T", requisition_number="REQ-T",
        requisition_date="2026-06-01",
    )
    EventBus.publish(
        PE.REQUISITION_CREATE,
        company_id=company.id,
        payload={
            "requisition_id": req.id,
            "requisition_number": req.requisition_number,
        },
    )
    call_command("process_events", "--once")

    # TASK-PROC-02-01 + transition → TASK-PROC-02-02
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-PROC-02-01",
    ).exists()
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-PROC-02-02",
    ).exists()