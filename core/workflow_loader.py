"""
Парсер YAML-workflow.

Читает файлы HR_Process_Workflow.yml, TASK_Process_Workflow.yml и т.д.
Преобразует в ProcessTaskDefinition и ProcessTaskTransition.

Формат входа (из HR_Process_Workflow.yml):

    processes:
      - id: HR-02
        tasks:
          - id: TASK-HR-02-01
            name: Приём сотрудника на работу
            role: hr_specialist
            form_ref: [OP-HR-12]
            sql_queries:
              on_hire: {query_code: OP-HR-12}
            transitions:
              - target_task: TASK-HR-02-06
                on_event: [on_hire]
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml
from django.db import transaction

from apps.tasks.models import ProcessTaskDefinition, ProcessTaskTransition

logger = logging.getLogger(__name__)


class WorkflowLoader:
    """
    Загружает один YAML-файл workflow в БД для указанной компании.
    Идемпотентен: повторный запуск обновляет существующие определения.
    """

    def __init__(self, company_id: int, module: str):
        self.company_id = company_id
        self.module = module
        self._definitions_cache: dict[str, ProcessTaskDefinition] = {}

    @transaction.atomic
    def load_file(self, path: Path) -> dict:
        """
        Загружает YAML-файл.
        Возвращает статистику: created, updated, transitions.
        """
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        processes = data.get("processes", [])
        if not processes:
            logger.warning("Workflow %s: нет процессов", path)
            return {"created": 0, "updated": 0, "transitions": 0}

        created = updated = transitions_count = 0

        # Первый проход: создаём/обновляем определения задач
        for process in processes:
            for order, task in enumerate(process.get("tasks", [])):
                _, was_created = self._upsert_definition(
                    process_code=process["id"],
                    task_data=task,
                    order=order,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        # Второй проход: создаём переходы (нужны все определения в БД)
        for process in processes:
            for task in process.get("tasks", []):
                source = self._definitions_cache.get(task["id"])
                if source is None:
                    continue
                for tr in task.get("transitions", []):
                    if self._upsert_transition(source, tr):
                        transitions_count += 1

        logger.info(
            "Workflow %s: created=%d, updated=%d, transitions=%d",
            path.name, created, updated, transitions_count,
        )
        return {
            "created": created,
            "updated": updated,
            "transitions": transitions_count,
        }

    def _upsert_definition(
        self, *, process_code: str, task_data: dict, order: int,
    ) -> tuple[ProcessTaskDefinition, bool]:
        """Создаёт или обновляет одно определение задачи."""
        code = task_data["id"]

        # Собираем события-триггеры из transitions.on_event
        # (из workflow мы знаем лишь внутренние псевдонимы вроде "on_hire";
        #  маппинг на реальный event_type делаем в handlers по form_refs/sql_queries)
        on_events = self._collect_trigger_events(task_data)

        defaults = {
            "process_code": process_code,
            "name": task_data.get("name", code),
            "description": task_data.get("description", ""),
            "role": task_data.get("role", ""),
            "form_refs": task_data.get("form_ref", []),
            "sql_queries": task_data.get("sql_queries", {}),
            "on_events": on_events,
            "order": order,
            "is_active": True,
        }

        obj, created = ProcessTaskDefinition.objects.update_or_create(
            company_id=self.company_id,
            code=code,
            defaults={"module": self.module, **defaults},
        )
        self._definitions_cache[code] = obj
        return obj, created

    def _upsert_transition(
        self, source: ProcessTaskDefinition, tr_data: dict,
    ) -> bool:
        """Создаёт или обновляет переход."""
        target_code = tr_data.get("target_task")
        if not target_code or target_code == "END_PROCESS":
            return False

        target = self._definitions_cache.get(target_code)
        if target is None:
            logger.warning(
                "Workflow: переход %s → %s не найден target",
                source.code, target_code,
            )
            return False

        _, created = ProcessTaskTransition.objects.update_or_create(
            company_id=self.company_id,
            source=source,
            target=target,
            defaults={
                "condition": tr_data.get("condition", ""),
                "on_events": tr_data.get("on_event", []),
            },
        )
        return created

    @staticmethod
    def _collect_trigger_events(task_data: dict) -> list[str]:
        """
        Извлекает реальные event_type из task_data.

        В YAML у задачи есть `sql_queries` с ключами вроде on_hire, on_transfer.
        Маппинг "on_hire" → "HR.employee.hire" делается через YAML-реестр,
        но проще: собираем уникальные on_* ключи и оставляем их как есть.
        Handlers сопоставляют их с реальными событиями через отдельный
        EVENT_ALIASES.
        """
        events = set()
        for key in (task_data.get("sql_queries") or {}).keys():
            events.add(key)
        return sorted(events)


# Реестр псевдонимов из YAML → реальные event_type.
# Используется в apps.tasks.handlers.
EVENT_ALIASES: dict[str, str] = {
    # HR
    "on_hire": "HR.employee.hire",
    "on_transfer": "HR.employee.transfer",
    "on_suspend": "HR.employee.suspend",
    "on_dismiss": "HR.employee.dismiss",
    "on_start_leave": "HR.employee.startLeave",
    "on_end_leave": "HR.employee.endLeave",
    "on_attach": "HR.employeeDocument.attach",
    "on_self_assess": "HR.employeeSkill.selfAssess",
    "on_confirm": "HR.employeeSkill.confirm",
    "on_score": "HR.employeeCompetencyScore.create",
    "on_assign": "HR.employeeQualification.assign",
    "on_extend": "HR.employeeQualification.extend",
    "on_issue": "HR.employeeCertificate.issue",
    "on_insert": "HR.medicalCheck.create",
    "on_request": "HR.employeeAbsence.request",
    "on_approve": "HR.employeeAbsence.review",
    "on_reject": "HR.employeeAbsence.review",
    "on_cancel": "HR.employeeAbsence.cancel",
    "on_submit": "HR.timesheet.submit",
    "on_update": "HR.timesheet.update",
    # TASK
    "on_start": "Task.task.start",
    "on_complete": "Task.task.complete",
    "on_comment": "Task.comment.save",
    "on_photo": "Task.photo.save",
    "on_time": "Task.timeTracking.save",
    "on_completion": "Task.task.updateCompletion",
}