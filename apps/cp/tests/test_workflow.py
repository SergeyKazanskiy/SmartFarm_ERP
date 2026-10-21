"""
Проверяем, что workflow корректно загружается и задачи создаются.
"""
from pathlib import Path

import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import CPEvents as CP
from core.workflow_loader import WorkflowLoader

from apps.tasks.models import ProcessTaskDefinition, TaskTask


WORKFLOW_DIR = Path("apps/cp/workflow")


@pytest.mark.django_db
def test_workflow_loads_and_resolves_events(company):
    loader = WorkflowLoader(
        company_id=company.id,
        module="CP",
        business_roles_path=WORKFLOW_DIR / "CP_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "CP_Process_Workflow.yml")

    # Должно быть 13 задач (по числу TASK-CP-* в YAML)
    assert ProcessTaskDefinition.objects.filter(company=company).count() == 13

    # TASK-CP-02-01 должна резолвиться в CP.counterparty.save
    task_def = ProcessTaskDefinition.objects.get(
        company=company, code="TASK-CP-02-01",
    )
    assert CP.COUNTERPARTY_SAVE in task_def.on_events


@pytest.mark.django_db
def test_task_created_on_counterparty_save(company):
    # Подготовка: справочники
    from apps.cp.models import Counterparty, CounterpartyType
    cp_type = CounterpartyType.objects.create(
        company=company, code="CPT-001", name="Клиент",
    )
    cp = Counterparty.objects.create(
        company=company, code="CP-001", name="X", counterparty_type=cp_type,
    )

    # Загружаем workflow
    loader = WorkflowLoader(
        company_id=company.id, module="CP",
        business_roles_path=WORKFLOW_DIR / "CP_Business_Roles.yml",
    )
    loader.load_file(WORKFLOW_DIR / "CP_Process_Workflow.yml")

    # Публикуем событие
    EventBus.publish(
        CP.COUNTERPARTY_SAVE,
        company_id=company.id,
        payload={"counterparty_id": cp.id, "name": cp.name},
    )

    # Прогоняем воркер
    call_command("process_events", "--once")

    # Должна создаться задача TASK-CP-02-01
    assert TaskTask.objects.filter(
        company=company, definition__code="TASK-CP-02-01",
    ).exists()