"""
Подписчики TASK-модуля.

Основная задача: при получении доменного события найти соответствующие
ProcessTaskDefinition и создать Task + уведомления для нужных ролей.
"""
import logging

from django.db import transaction

from core.event_bus import DomainEvent, EventBus
from core.workflow_loader import EVENT_ALIASES

from apps.tasks.models import (
    ProcessTaskDefinition, TaskAssignment, TaskNotification, TaskTask,
)

logger = logging.getLogger(__name__)


# Реверс-маппинг: event_type → псевдонимы, которые могут быть в on_events
# (собираем из EVENT_ALIASES наоборот).
# REVERSE_ALIASES: dict[str, list[str]] = {} ???
# for alias, event_type in EVENT_ALIASES.items():
#     REVERSE_ALIASES.setdefault(event_type, []).append(alias)


class TaskCreator:
    """
    Создаёт задачи по событию.
    Идемпотентен: если задача для (event, source_id, definition) уже есть —
    повторно не создаёт.
    """

    @classmethod
    @transaction.atomic
    def create_from_event(cls, event: DomainEvent) -> list[TaskTask]:
        # aliases = REVERSE_ALIASES.get(event.event_type, [])
        # if not aliases:
        #     return []

    # Ищем определения, у которых on_events содержит наш event_type.
        # ArrayField: __contains=[event_type] означает «в массиве есть элемент».
        definitions = ProcessTaskDefinition.objects.filter(
            company_id=event.company_id,
            is_active=True,
            on_events__contains=[event.event_type],
        )
        # Ищем определения, у которых on_events пересекается с aliases
        # definitions = ProcessTaskDefinition.objects.filter(
        #     company_id=event.company_id,
        #     is_active=True,
        #     on_events__overlap=aliases,   # JSONB overlap для PostgreSQL
        # )

        created_tasks = []
        for definition in definitions:
            task = cls._create_one(definition, event)
            if task:
                created_tasks.append(task)
        return created_tasks

    @classmethod
    def _create_one(
        cls, definition: ProcessTaskDefinition, event: DomainEvent,
    ) -> TaskTask | None:
        source_id = event.payload.get("employee_id") or event.payload.get("source_id")

        # Идемпотентность: не создаём дубликат
        if source_id and TaskTask.objects.filter(
            company_id=event.company_id,
            definition=definition,
            source_id=source_id,
            status__in=["created", "assigned", "in_progress", "on_hold"],
        ).exists():
            logger.debug("Задача %s для source=%s уже создана", definition.code, source_id)
            return None

        # Название задачи — из определения, но можно подставить контекст
        task_name = definition.name
        if source_id:
            task_name = f"{definition.name} (ID: {source_id})"

        task = TaskTask.objects.create(
            company_id=event.company_id,
            definition=definition,
            source_type="hr",
            source_id=source_id,
            task_name=task_name,
            description=definition.description,
            status="created",
            assigned_role=definition.role,
        )

        # Находим сотрудников подходящей роли и уведомляем
        cls._notify_role(definition.role, task, event)

        logger.info(
            "Создана задача %s по событию %s (company=%s)",
            task.id, event.event_type, event.company_id,
        )
        return task

    @classmethod
    def _notify_role(cls, role: str, task: TaskTask, event: DomainEvent) -> None:
        """
        Ищем сотрудников с нужной ролью и создаём уведомления.
        На текущем этапе — используем hr_employee_id из User:
        ищем через связь User.hr_employee_id и Groups.
        """
        from apps.companies.models import User

        # Пользователи с ролью (группой) в этой компании
        users = User.objects.filter(
            is_active=True,
            companies__id=task.company_id,
            groups__name=role,
            hr_employee_id__isnull=False,
        ).distinct()

        for user in users:
            TaskNotification.objects.create(
                company_id=task.company_id,
                task=task,
                employee_id=user.hr_employee_id,
                notification_type="assigned",
                message=f"Новая задача: {task.task_name}",
            )


# ============================================================
# Регистрация подписчиков
# ============================================================

@EventBus.subscribe("HR.employee.hire")
def on_hr_employee_hire(event: DomainEvent) -> None:
    """При приёме сотрудника создаём задачи HR-специалисту."""
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.employee.dismiss")
def on_hr_employee_dismiss(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.employee.startLeave")
def on_hr_employee_start_leave(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.employeeAbsence.request")
def on_hr_absence_request(event: DomainEvent) -> None:
    """Заявка на отсутствие → задача руководителю подразделения."""
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.timesheet.submit")
def on_hr_timesheet_submit(event: DomainEvent) -> None:
    """Табель отправлен → задача руководителю на утверждение."""
    TaskCreator.create_from_event(event)


@EventBus.subscribe("Task.task.complete")
def on_task_complete(event: DomainEvent) -> None:
    """
    Задача завершена → ищем переходы в workflow.
    Например: завершён табель → создать следующую задачу (Payroll).
    На текущем этапе — заглушка, будет расширена в модулях FIN/APS.
    """
    logger.info("Обработка события Task.task.complete для task_id=%s", event.payload.get("task_id"))