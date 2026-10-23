"""
Загрузка workflow CRM и проверка резолвинга on_events.
"""
from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import CRMEvents as CRM
from core.workflow_loader import WorkflowLoader

from apps.crm.models import Lead, LeadStatus
from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/crm/workflow")


@pytest.mark.django_db
def test_workflow_loads_and_resolves_events(company):
    loader = WorkflowLoader(
        company_id=company.id,
        module="CRM",
        business_roles_path=WORKFLOW_DIR / "CRM_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "CRM_Process_Workflow.yml")

    # Ожидаем 17 задач (по количеству TASK-CRM-* в YAML)
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 17

    # TASK-CRM-01-01 должна резолвиться в CRM.lead.create
    d = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-CRM-01-01",
    )
    assert CRM.LEAD_CREATE in d.on_events


@pytest.mark.django_db
def test_task_created_on_lead_create(company, lead_status):
    # workflow
    loader = WorkflowLoader(
        company_id=company.id, module="CRM",
        business_roles_path=WORKFLOW_DIR / "CRM_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "CRM_Process_Workflow.yml")

    lead = Lead.objects.create(
        company=company, code="LEAD-X", lead_status=lead_status,
    )
    EventBus.publish(
        CRM.LEAD_CREATE,
        company_id=company.id,
        payload={"lead_id": lead.id, "code": lead.code},
    )
    call_command("process_events", "--once")

    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-CRM-01-01",
    ).exists()