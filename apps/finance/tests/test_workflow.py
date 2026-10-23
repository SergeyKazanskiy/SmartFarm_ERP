from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import FinanceEvents as FE
from core.workflow_loader import WorkflowLoader

from apps.finance.models import Invoice
from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/finance/workflow")


@pytest.mark.django_db
def test_workflow_loads(company):
    loader = WorkflowLoader(
        company_id=company.id, module="FINANCE",
        business_roles_path=WORKFLOW_DIR / "Finance_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "Finance_Process_Workflow.yml")

    # В Finance_Process_Workflow.yml: 15 задач
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 15

    d = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-FIN-03-01",
    )
    assert FE.INVOICE_CREATE in d.on_events


@pytest.mark.django_db
def test_task_created_on_invoice_create(company, counterparty):
    loader = WorkflowLoader(
        company_id=company.id, module="FINANCE",
        business_roles_path=WORKFLOW_DIR / "Finance_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "Finance_Process_Workflow.yml")

    inv = Invoice.objects.create(
        company=company, code="FINV-X", invoice_type="AP",
        counterparty_id=counterparty.id,
        invoice_date="2026-06-01", amount=100,
    )
    EventBus.publish(
        FE.INVOICE_CREATE,
        company_id=company.id,
        payload={"invoice_id": inv.id, "invoice_type": "AP", "amount": 100},
    )
    call_command("process_events", "--once")

    # TASK-FIN-03-01 (создание счёта) + TASK-FIN-03-02 (добавление позиции через transition)
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-FIN-03-01",
    ).exists()