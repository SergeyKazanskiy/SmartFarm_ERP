from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import SalesEvents as SE
from core.workflow_loader import WorkflowLoader

from apps.sales.models import Customer
from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/sales/workflow")


@pytest.mark.django_db
def test_workflow_loads(company):
    loader = WorkflowLoader(
        company_id=company.id, module="SALES",
        business_roles_path=WORKFLOW_DIR / "SALES_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "SALES_Process_Workflow.yml")

    # В SALES_Process_Workflow.yml: 11 задач
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 11

    d = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-SALES-02-01",
    )
    assert SE.OPPORTUNITY_CREATE in d.on_events


@pytest.mark.django_db
def test_task_created_on_customer_save(company, counterparty):
    loader = WorkflowLoader(
        company_id=company.id, module="SALES",
        business_roles_path=WORKFLOW_DIR / "SALES_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "SALES_Process_Workflow.yml")

    cust = Customer.objects.create(
        company=company, code="CUST-X",
        counterparty_id=counterparty.id,
    )
    EventBus.publish(
        SE.CUSTOMER_SAVE,
        company_id=company.id,
        payload={"customer_id": cust.id, "code": cust.code},
    )
    call_command("process_events", "--once")

    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-SALES-01-01",
    ).exists()