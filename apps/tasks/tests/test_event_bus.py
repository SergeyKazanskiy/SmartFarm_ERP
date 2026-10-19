"""
Тесты Event Bus (Outbox Pattern) и создания задач из событий.
"""
import pytest
from django.contrib.auth.models import Group

from core.event_bus import DomainEvent, EventBus
from core.events import HREvents as HR

from apps.tasks.handlers import TaskCreator
from apps.tasks.models import ProcessTaskDefinition, TaskNotification, TaskTask


@pytest.mark.django_db
def test_publish_writes_event(company):
    event = EventBus.publish(
        HR.EMPLOYEE_HIRE, company_id=company.id,
        payload={"employee_id": 1},
    )
    assert event.id is not None
    assert event.status == DomainEvent.STATUS_PENDING
    assert DomainEvent.objects.filter(id=event.id).exists()


@pytest.mark.django_db
def test_task_created_on_hire_event(company):
    # Создаём определение из workflow
    definition = ProcessTaskDefinition.objects.create(
        company=company,
        module="HR",
        process_code="HR-02",
        code="TASK-HR-02-06",
        name="Прикрепить кадровый документ",
        role="hr_specialist",
        on_events=["on_hire"],
    )

    # Создаём событие
    event = DomainEvent.objects.create(
        event_type=HR.EMPLOYEE_HIRE,
        company=company,
        payload={"employee_id": 42},
    )

    # Диспатчим
    TaskCreator.create_from_event(event)

    task = TaskTask.objects.get(definition=definition)
    assert task.source_id == 42
    assert task.assigned_role == "hr_specialist"
    assert task.status == "created"


@pytest.mark.django_db
def test_task_idempotency(company):
    definition = ProcessTaskDefinition.objects.create(
        company=company, module="HR", process_code="HR-02",
        code="TASK-HR-02-06", name="X", role="hr_specialist",
        on_events=["on_hire"],
    )
    event = DomainEvent.objects.create(
        event_type=HR.EMPLOYEE_HIRE, company=company,
        payload={"employee_id": 42},
    )

    TaskCreator.create_from_event(event)
    TaskCreator.create_from_event(event)
    TaskCreator.create_from_event(event)

    assert TaskTask.objects.filter(definition=definition).count() == 1


@pytest.mark.django_db
def test_notification_sent_to_role(company, user):
    """Пользователь в группе hr_specialist получает уведомление."""
    group = Group.objects.create(name="hr_specialist")
    user.groups.add(group)

    definition = ProcessTaskDefinition.objects.create(
        company=company, module="HR", process_code="HR-02",
        code="TASK-HR-02-06", name="X", role="hr_specialist",
        on_events=["on_hire"],
    )
    event = DomainEvent.objects.create(
        event_type=HR.EMPLOYEE_HIRE, company=company,
        payload={"employee_id": 42},
    )
    TaskCreator.create_from_event(event)

    task = TaskTask.objects.get(definition=definition)
    assert TaskNotification.objects.filter(
        task=task, employee_id=user.hr_employee_id,
    ).exists()