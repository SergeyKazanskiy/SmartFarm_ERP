"""
Подписчики TASK-модуля.

При получении доменного события:
1. Находит ProcessTaskDefinition с on_events, содержащим event_type.
2. Создаёт TaskTask по каждому такому определению (source-задачи).
3. Для каждой source-задачи обрабатывает ProcessTaskTransition:
   если transition.on_events (псевдонимы) пересекается с алиасами события
   в контексте source-определения — создаёт target-задачу.

Идемпотентность на всех уровнях: повторное событие не создаёт дубликатов.
"""
import logging

from django.db import transaction

from core.event_bus import DomainEvent, EventBus

from apps.tasks.models import (
    ProcessTaskDefinition, ProcessTaskTransition,
    TaskAssignment, TaskNotification, TaskTask,
)

logger = logging.getLogger(__name__)


# Маппинг префикса event_type → source_type. Используется для TaskTask.source_type.
_KNOWN_SOURCE_TYPES = {
    "hr", "task", "cp", "crm", "pm",
    "aps", "wms", "fin", "os", "toip",
    "production", "sales", "fleet", "construction",
}


class TaskCreator:
    """
    Создаёт задачи и каскадирует переходы по workflow.
    Идемпотентен: повторный вызов с тем же событием не создаёт дубликатов.
    """

    # ------------------------------------------------------------
    # Точка входа
    # ------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def create_from_event(cls, event: DomainEvent) -> list[TaskTask]:
        """
        Создаёт source-задачи по событию и запускает transitions.
        Возвращает список созданных задач (source + target).
        """
        definitions = ProcessTaskDefinition.objects.filter(
            company_id=event.company_id,
            is_active=True,
            on_events__contains=[event.event_type],
        )

        created_tasks: list[TaskTask] = []

        for definition in definitions:
            source_task = cls._create_one(definition, event)
            if source_task is None:
                # source уже существует → transition НЕ запускаем
                continue

            created_tasks.append(source_task)
            cls._create_transitions(
                source_definition=definition,
                source_task=source_task,
                event=event,
                out_list=created_tasks,
            )

        return created_tasks

    # ------------------------------------------------------------
    # Создание source-задачи
    # ------------------------------------------------------------

    @classmethod
    def _create_one(
        cls, definition: ProcessTaskDefinition, event: DomainEvent,
    ) -> TaskTask | None:
        """
        Создаёт одну задачу по определению.
        Возвращает None, если такая активная задача уже есть.
        """
        source_id = (
            event.payload.get("employee_id")
            or event.payload.get("source_id")
        )
        # Универсальный fallback: ищем любой ключ, оканчивающийся на "_id"
        # (project_id, counterparty_id, lead_id, opportunity_id, …)
        if source_id is None:
            for key, value in event.payload.items():
                if key.endswith("_id") and isinstance(value, int):
                    source_id = value
                    break

        if source_id and cls._active_task_exists(
            event.company_id, definition, source_id,
        ):
            logger.debug(
                "TaskCreator: %s для source=%s уже активна",
                definition.code, source_id,
            )
            return None

        task = cls._do_create(definition, source_id, event)
        cls._notify_role(definition.role, task, event)
        logger.info(
            "TaskCreator: создана source-задача %s (%s) по событию %s",
            task.id, definition.code, event.event_type,
        )
        return task

    # ------------------------------------------------------------
    # Создание target-задач через transitions
    # ------------------------------------------------------------

    @classmethod
    def _create_transitions(
        cls,
        *,
        source_definition: ProcessTaskDefinition,
        source_task: TaskTask,
        event: DomainEvent,
        out_list: list[TaskTask],
    ) -> None:
        """
        Для каждой ProcessTaskTransition из source_definition:
        - проверяет, что transition.on_events (псевдонимы) пересекается
          с алиасами текущего события в контексте source_definition;
        - если да — создаёт target-задачу с тем же source_id.
        """
        # Алиасы текущего события для source-задачи:
        # source.event_aliases = {"on_insert": "PM.project.save"}
        # event.event_type = "PM.project.save"
        # → event_aliases_for_source = {"on_insert"}
        event_aliases_for_source = {
            alias
            for alias, evt in (source_definition.event_aliases or {}).items()
            if evt == event.event_type
        }
        if not event_aliases_for_source:
            logger.debug(
                "TaskCreator: у %s нет алиасов для %s, transitions пропущены",
                source_definition.code, event.event_type,
            )
            return

        transitions = (
            ProcessTaskTransition.objects
            .filter(company_id=event.company_id, source=source_definition)
            .select_related("target")
        )

        for tr in transitions:
            transition_events = set(tr.on_events or [])
            if not transition_events.intersection(event_aliases_for_source):
                continue

            target_task = cls._create_one_from_transition(
                definition=tr.target,
                source_id=source_task.source_id,
                event=event,
            )
            if target_task:
                out_list.append(target_task)
                logger.info(
                    "TaskCreator: transition %s → %s, создана target %s",
                    source_definition.code, tr.target.code, target_task.id,
                )

    @classmethod
    def _create_one_from_transition(
        cls,
        *,
        definition: ProcessTaskDefinition,
        source_id: int | None,
        event: DomainEvent,
    ) -> TaskTask | None:
        """
        Создаёт target-задачу по определению из transition.
        Отличие от _create_one: source_id уже известен, алиасы не пересчитываем.
        """
        if source_id and cls._active_task_exists(
            event.company_id, definition, source_id,
        ):
            logger.debug(
                "TaskCreator: target %s для source=%s уже существует",
                definition.code, source_id,
            )
            return None

        task = cls._do_create(definition, source_id, event)
        cls._notify_role(definition.role, task, event)
        return task

    # ------------------------------------------------------------
    # Общие утилиты
    # ------------------------------------------------------------

    @classmethod
    def _do_create(
        cls,
        definition: ProcessTaskDefinition,
        source_id: int | None,
        event: DomainEvent,
    ) -> TaskTask:
        """Непосредственно создаёт TaskTask. Без проверок."""
        task_name = definition.name
        if source_id:
            task_name = f"{definition.name} (ID: {source_id})"

        return TaskTask.objects.create(
            company_id=event.company_id,
            definition=definition,
            source_type=cls._derive_source_type(event.event_type),
            source_id=source_id,
            task_name=task_name,
            description=definition.description,
            status="created",
            assigned_role=definition.role,
        )

    @staticmethod
    def _derive_source_type(event_type: str) -> str:
        """'PM.project.save' → 'pm'; 'HR.employee.hire' → 'hr'."""
        prefix = event_type.split(".", 1)[0].lower()
        return prefix if prefix in _KNOWN_SOURCE_TYPES else "manual"

    @staticmethod
    def _active_task_exists(
        company_id: int,
        definition: ProcessTaskDefinition,
        source_id: int,
    ) -> bool:
        """Есть ли уже активная задача для (definition, source_id)."""
        return TaskTask.objects.filter(
            company_id=company_id,
            definition=definition,
            source_id=source_id,
            status__in=["created", "assigned", "in_progress", "on_hold"],
        ).exists()

    @classmethod
    def _notify_role(cls, role: str, task: TaskTask, event: DomainEvent) -> None:
        """Уведомляет сотрудников с нужной ролью."""
        from apps.companies.models import User

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
    """Приём сотрудника → задачи HR-специалисту."""
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.employee.dismiss")
def on_hr_employee_dismiss(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.employee.startLeave")
def on_hr_employee_start_leave(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.employeeAbsence.request")
def on_hr_absence_request(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("HR.timesheet.submit")
def on_hr_timesheet_submit(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("CP.counterparty.save")
def on_cp_counterparty_save(event: DomainEvent) -> None:
    """Создание контрагента → задачи менеджеру."""
    TaskCreator.create_from_event(event)


@EventBus.subscribe("CP.blacklist.add")
def on_cp_blacklist_add(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("CRM.lead.create")
def on_crm_lead_create(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("CRM.opportunity.create")
def on_crm_opportunity_create(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("CRM.opportunity.win")
def on_crm_opportunity_win(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("PM.project.save")
def on_pm_project_save(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("PM.task.save")
def on_pm_task_save(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)


@EventBus.subscribe("PM.resourceNeed.sendToAPS")
def on_pm_resource_need_send(event: DomainEvent) -> None:
    TaskCreator.create_from_event(event)