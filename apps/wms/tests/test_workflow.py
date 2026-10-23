from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import WMSEvents as WE
from core.workflow_loader import WorkflowLoader

from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/wms/workflow")


@pytest.mark.django_db
def test_workflow_loads(company):
    loader = WorkflowLoader(
        company_id=company.id, module="WMS",
        business_roles_path=WORKFLOW_DIR / "WMS_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "WMS_Process_Workflow.yml")

    # 17 задач в WMS_Process_Workflow.yml
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 17

    d = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-WMS-02-01",
    )
    assert WE.GOODS_RECEIPT_CREATE in d.on_events


@pytest.mark.django_db
def test_task_created_on_receipt_create(company, warehouse):
    loader = WorkflowLoader(
        company_id=company.id, module="WMS",
        business_roles_path=WORKFLOW_DIR / "WMS_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "WMS_Process_Workflow.yml")

    from apps.wms.models import GoodsReceipt
    gr = GoodsReceipt.objects.create(
        company=company, code="GR-T", warehouse=warehouse,
        receipt_date="2026-06-01T10:00:00Z",
    )
    EventBus.publish(
        WE.GOODS_RECEIPT_CREATE,
        company_id=company.id,
        payload={"receipt_id": gr.id, "warehouse_id": warehouse.id},
    )
    call_command("process_events", "--once")

    # Создаётся TASK-WMS-02-01 + TASK-WMS-02-02 через transition
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-WMS-02-01",
    ).exists()
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-WMS-02-02",
    ).exists()