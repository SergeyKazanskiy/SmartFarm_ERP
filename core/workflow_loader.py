"""
Парсер YAML-workflow.

Читает Business_Roles (маппинг op_code → event_type) и Process_Workflow
(задачи и переходы). Резолвит on_* алиасы в реальные event_type.
"""
from __future__ import annotations

import logging
from pathlib import Path

import yaml
from django.db import transaction

from apps.tasks.models import ProcessTaskDefinition, ProcessTaskTransition

logger = logging.getLogger(__name__)


class BusinessRolesIndex:
    """Индекс op_code → event_type из Business_Roles.yml."""

    def __init__(self, path: Path):
        self.op_code_to_event: dict[str, str] = {}
        self.op_code_to_table: dict[str, str] = {}
        self._load(path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            logger.warning("Business_Roles не найден: %s", path)
            return
        with open(path, "r", encoding="utf-8") as f:
            for doc in yaml.safe_load_all(f):
                if not doc:
                    continue
                for op in doc.get("operations", []):
                    codes = op["op_code"]
                    if isinstance(codes, str):
                        codes = [codes]
                    event = op.get("event")
                    table = op.get("table")
                    for code in codes:
                        self.op_code_to_event[code] = event
                        self.op_code_to_table[code] = table
        logger.info("Business_Roles: загружено %d операций", len(self.op_code_to_event))


class WorkflowLoader:
    """
    Загружает YAML-workflow в БД для указанной компании.
    Идемпотентен: повторный запуск обновляет существующие определения.
    """

    def __init__(self, company_id: int, module: str,
                 business_roles_path: Path | None = None):
        self.company_id = company_id
        self.module = module
        self._definitions_cache: dict[str, ProcessTaskDefinition] = {}
        self.business_roles = (
            BusinessRolesIndex(business_roles_path)
            if business_roles_path else None
        )

    @transaction.atomic
    def load_file(self, path: Path) -> dict:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        processes = data.get("processes", [])
        if not processes:
            logger.warning("Workflow %s: нет процессов", path)
            return {"created": 0, "updated": 0, "transitions": 0}

        created = updated = transitions_count = 0

        # Проход 1: определения
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

        # Проход 2: переходы
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
        code = task_data["id"]
        on_events, aliases = self._resolve_events(task_data)

        defaults = {
            "process_code": process_code,
            "name": task_data.get("name", code),
            "description": task_data.get("description", ""),
            "role": task_data.get("role", ""),
            "form_refs": task_data.get("form_ref", []),
            "sql_queries": task_data.get("sql_queries", {}),
            "on_events": on_events,
            "event_aliases": aliases,
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

    def _resolve_events(self, task_data: dict) -> tuple[list[str], dict[str, str]]:
        """
        Извлекает реальные event_type из task_data.

        Логика:
        1. Для каждого on_* в sql_queries берём query_code (= op_code).
        2. По op_code находим event в Business_Roles.
        3. Дополнительно подтягиваем события из form_ref (там тоже op_code).
        """
        on_events: set[str] = set()
        aliases: dict[str, str] = {}

        if self.business_roles is None:
            # Без Business_Roles — оставляем алиасы как есть
            for alias in (task_data.get("sql_queries") or {}).keys():
                aliases[alias] = alias
                on_events.add(alias)
            return sorted(on_events), aliases

        # 1. sql_queries
        for alias, query in (task_data.get("sql_queries") or {}).items():
            codes = query.get("query_code") if isinstance(query, dict) else None
            if codes is None:
                continue
            if isinstance(codes, str):
                codes = [codes]
            for op_code in codes:
                event = self.business_roles.op_code_to_event.get(op_code)
                if event:
                    on_events.add(event)
                    aliases[alias] = event

        # 2. form_ref (fallback, если для операции нет явного on_*)
        for op_code in task_data.get("form_ref", []) or []:
            event = self.business_roles.op_code_to_event.get(op_code)
            if event:
                on_events.add(event)
                aliases.setdefault(f"form_ref:{op_code}", event)

        return sorted(on_events), aliases

    def _upsert_transition(
        self, source: ProcessTaskDefinition, tr_data: dict,
    ) -> bool:
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


# Больше не нужен: EVENT_ALIASES. Резолвинг теперь через Business_Roles.





# """
# Парсер YAML-workflow.

# Читает файлы HR_Process_Workflow.yml, TASK_Process_Workflow.yml и т.д.
# Преобразует в ProcessTaskDefinition и ProcessTaskTransition.

# Формат входа (из HR_Process_Workflow.yml):

#     processes:
#       - id: HR-02
#         tasks:
#           - id: TASK-HR-02-01
#             name: Приём сотрудника на работу
#             role: hr_specialist
#             form_ref: [OP-HR-12]
#             sql_queries:
#               on_hire: {query_code: OP-HR-12}
#             transitions:
#               - target_task: TASK-HR-02-06
#                 on_event: [on_hire]
# """
# from __future__ import annotations

# import logging
# from pathlib import Path

# import yaml
# from django.db import transaction

# from apps.tasks.models import ProcessTaskDefinition, ProcessTaskTransition

# logger = logging.getLogger(__name__)


# class WorkflowLoader:
#     """
#     Загружает один YAML-файл workflow в БД для указанной компании.
#     Идемпотентен: повторный запуск обновляет существующие определения.
#     """

#     def __init__(self, company_id: int, module: str):
#         self.company_id = company_id
#         self.module = module
#         self._definitions_cache: dict[str, ProcessTaskDefinition] = {}

#     @transaction.atomic
#     def load_file(self, path: Path) -> dict:
#         """
#         Загружает YAML-файл.
#         Возвращает статистику: created, updated, transitions.
#         """
#         with open(path, "r", encoding="utf-8") as f:
#             data = yaml.safe_load(f)

#         processes = data.get("processes", [])
#         if not processes:
#             logger.warning("Workflow %s: нет процессов", path)
#             return {"created": 0, "updated": 0, "transitions": 0}

#         created = updated = transitions_count = 0

#         # Первый проход: создаём/обновляем определения задач
#         for process in processes:
#             for order, task in enumerate(process.get("tasks", [])):
#                 _, was_created = self._upsert_definition(
#                     process_code=process["id"],
#                     task_data=task,
#                     order=order,
#                 )
#                 if was_created:
#                     created += 1
#                 else:
#                     updated += 1

#         # Второй проход: создаём переходы (нужны все определения в БД)
#         for process in processes:
#             for task in process.get("tasks", []):
#                 source = self._definitions_cache.get(task["id"])
#                 if source is None:
#                     continue
#                 for tr in task.get("transitions", []):
#                     if self._upsert_transition(source, tr):
#                         transitions_count += 1

#         logger.info(
#             "Workflow %s: created=%d, updated=%d, transitions=%d",
#             path.name, created, updated, transitions_count,
#         )
#         return {
#             "created": created,
#             "updated": updated,
#             "transitions": transitions_count,
#         }

#     def _upsert_definition(
#         self, *, process_code: str, task_data: dict, order: int,
#     ) -> tuple[ProcessTaskDefinition, bool]:
#         """Создаёт или обновляет одно определение задачи."""
#         code = task_data["id"]

#         # Собираем события-триггеры из transitions.on_event
#         # (из workflow мы знаем лишь внутренние псевдонимы вроде "on_hire";
#         #  маппинг на реальный event_type делаем в handlers по form_refs/sql_queries)
#         on_events = self._collect_trigger_events(task_data)

#         defaults = {
#             "process_code": process_code,
#             "name": task_data.get("name", code),
#             "description": task_data.get("description", ""),
#             "role": task_data.get("role", ""),
#             "form_refs": task_data.get("form_ref", []),
#             "sql_queries": task_data.get("sql_queries", {}),
#             "on_events": on_events,
#             "order": order,
#             "is_active": True,
#         }

#         obj, created = ProcessTaskDefinition.objects.update_or_create(
#             company_id=self.company_id,
#             code=code,
#             defaults={"module": self.module, **defaults},
#         )
#         self._definitions_cache[code] = obj
#         return obj, created

#     def _upsert_transition(
#         self, source: ProcessTaskDefinition, tr_data: dict,
#     ) -> bool:
#         """Создаёт или обновляет переход."""
#         target_code = tr_data.get("target_task")
#         if not target_code or target_code == "END_PROCESS":
#             return False

#         target = self._definitions_cache.get(target_code)
#         if target is None:
#             logger.warning(
#                 "Workflow: переход %s → %s не найден target",
#                 source.code, target_code,
#             )
#             return False

#         _, created = ProcessTaskTransition.objects.update_or_create(
#             company_id=self.company_id,
#             source=source,
#             target=target,
#             defaults={
#                 "condition": tr_data.get("condition", ""),
#                 "on_events": tr_data.get("on_event", []),
#             },
#         )
#         return created

#     @staticmethod
#     def _collect_trigger_events(task_data: dict) -> list[str]:
#         """
#         Извлекает реальные event_type из task_data.

#         В YAML у задачи есть `sql_queries` с ключами вроде on_hire, on_transfer.
#         Маппинг "on_hire" → "HR.employee.hire" делается через YAML-реестр,
#         но проще: собираем уникальные on_* ключи и оставляем их как есть.
#         Handlers сопоставляют их с реальными событиями через отдельный
#         EVENT_ALIASES.
#         """
#         events = set()
#         for key in (task_data.get("sql_queries") or {}).keys():
#             events.add(key)
#         return sorted(events)


# # Реестр псевдонимов из YAML → реальные event_type.
# # Используется в apps.tasks.handlers.
# EVENT_ALIASES: dict[str, str] = {
#     # HR
#     "on_hire": "HR.employee.hire",
#     "on_transfer": "HR.employee.transfer",
#     "on_suspend": "HR.employee.suspend",
#     "on_dismiss": "HR.employee.dismiss",
#     "on_start_leave": "HR.employee.startLeave",
#     "on_end_leave": "HR.employee.endLeave",
#     "on_attach": "HR.employeeDocument.attach",
#     "on_self_assess": "HR.employeeSkill.selfAssess",
#     "on_confirm": "HR.employeeSkill.confirm",
#     "on_score": "HR.employeeCompetencyScore.create",
#     "on_assign": "HR.employeeQualification.assign",
#     "on_extend": "HR.employeeQualification.extend",
#     "on_issue": "HR.employeeCertificate.issue",
#     "on_insert": "HR.medicalCheck.create",
#     "on_request": "HR.employeeAbsence.request",
#     "on_approve": "HR.employeeAbsence.review",
#     "on_reject": "HR.employeeAbsence.review",
#     "on_cancel": "HR.employeeAbsence.cancel",
#     "on_submit": "HR.timesheet.submit",
#     "on_update": "HR.timesheet.update",
#     # TASK
#     "on_start": "Task.task.start",
#     "on_complete": "Task.task.complete",
#     "on_comment": "Task.comment.save",
#     "on_photo": "Task.photo.save",
#     "on_time": "Task.timeTracking.save",
#     "on_completion": "Task.task.updateCompletion",
# }