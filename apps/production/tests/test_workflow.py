from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import ProductionEvents as PRE
from core.workflow_loader import WorkflowLoader

from apps.production.models import ProductionOrder
from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/production/workflow")


@pytest.mark.django_db
def test_workflow_loads(company):
    loader = WorkflowLoader(
        company_id=company.id, module="PRODUCTION",
        business_roles_path=WORKFLOW_DIR / "Production_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "Production_Process_Workflow.yml")

    # 22 задачи в Production_Process_Workflow.yml
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 22

    d = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-PROD-03-01",
    )
    assert PRE.PRODUCTION_ORDER_CREATE in d.on_events


@pytest.mark.django_db
def test_task_created_on_production_order_create(company, bom, routing):
    loader = WorkflowLoader(
        company_id=company.id, module="PRODUCTION",
        business_roles_path=WORKFLOW_DIR / "Production_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "Production_Process_Workflow.yml")

    order = ProductionOrder.objects.create(
        company=company, code="PROD-T", bom=bom, routing=routing,
        planned_quantity=10, status="draft",
    )
    EventBus.publish(
        PRE.PRODUCTION_ORDER_CREATE,
        company_id=company.id,
        payload={
            "production_order_id": order.id,
            "bom_id": bom.id,
            "planned_quantity": 10,
        },
    )
    call_command("process_events", "--once")

    # TASK-PROD-03-01 + transition → TASK-PROD-03-02
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-PROD-03-01",
    ).exists()
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-PROD-03-02",
    ).exists()