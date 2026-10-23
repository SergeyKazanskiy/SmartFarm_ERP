# """
# Тест воркера process_events: обрабатывает pending, помечает processed.
# """
# import pytest
# from django.core.management import call_command

# from core.event_bus import DomainEvent, EventBus
# from core.events import HREvents as HR
# from core.events import PMEvents as PM  # <-- 1. ДОБАВИЛИ ИМПОРТ PM (Проверьте, откуда импортируются события PM)

# # <-- 2. ДОБАВИЛИ ИМПОРТЫ МОДЕЛЕЙ И КЛАССОВ (Замените пути на ваши реальные приложения)
# from core.workflow_loader import WorkflowLoader  # Укажите ваш путь к WorkflowLoader
# from apps.pm. import WORKFLOW_DIR  # Укажите ваш путь к WORKFLOW_DIR
# from apps.pm.models import Project                # Укажите ваш путь к модели Project
# from apps.tasks.models import TaskTask            # Укажите ваш путь к модели TaskTask



# @pytest.mark.django_db
# def test_transition_creates_next_step(company):
#     """
#     PM.project.save → создаются:
#     - TASK-PM-01-01 (source)
#     - TASK-PM-02-01 (target через transition с on_event=[on_insert])
#     """
#     loader = WorkflowLoader(
#         company_id=company.id, module="PM",
#         business_roles_path=WORKFLOW_DIR / "PM_Business_Roles.yml",
#     )
#     loader.load_file(WORKFLOW_DIR / "PM_Process_Workflow.yml")

#     p = Project.objects.create(
#         company=company, code="PROJ-X", name="X",
#     )
#     EventBus.publish(
#         PM.PROJECT_SAVE,  # Теперь PM импортирован и не вызовет NameError
#         company_id=company.id,
#         payload={"project_id": p.id, "code": p.code, "status": "planning"},
#     )
#     call_command("process_events", "--once")

#     # Обе задачи созданы
#     source = TaskTask.objects.get(
#         company=company, definition__code="TASK-PM-01-01",
#     )
#     target = TaskTask.objects.get(
#         company=company, definition__code="TASK-PM-02-01",
#     )

#     assert source.source_id == p.id
#     assert target.source_id == p.id
#     assert source.source_type == "pm"
#     assert target.source_type == "pm"
#     assert source.assigned_role == "project_manager"
#     assert target.assigned_role == "project_manager"



# @pytest.mark.django_db
# def test_transition_idempotent(company):
#     """
#     Повторное событие PM.project.save не создаёт дубликатов
#     ни source, ни target.
#     """
#     loader = WorkflowLoader(
#         company_id=company.id, module="PM",
#         business_roles_path=WORKFLOW_DIR / "PM_Business_Roles.yml",
#     )
#     loader.load_file(WORKFLOW_DIR / "PM_Process_Workflow.yml")

#     p = Project.objects.create(company=company, code="PROJ-X", name="X")

#     for _ in range(3):
#         EventBus.publish(
#             PM.PROJECT_SAVE,
#             company_id=company.id,
#             payload={"project_id": p.id},
#         )

#     call_command("process_events", "--once")

#     assert TaskTask.objects.filter(
#         company=company, definition__code="TASK-PM-01-01",
#     ).count() == 1
#     assert TaskTask.objects.filter(
#         company=company, definition__code="TASK-PM-02-01",
#     ).count() == 1


# @pytest.mark.django_db
# def test_transition_not_fired_if_source_exists(company):
#     """
#     Если source-задача уже активна, а событие пришло повторно —
#     transition не запускается повторно (target не создаётся).
#     """
#     loader = WorkflowLoader(
#         company_id=company.id, module="PM",
#         business_roles_path=WORKFLOW_DIR / "PM_Business_Roles.yml",
#     )
#     loader.load_file(WORKFLOW_DIR / "PM_Process_Workflow.yml")

#     p = Project.objects.create(company=company, code="PROJ-X", name="X")

#     # Первое событие — создаёт source и target
#     EventBus.publish(
#         PM.PROJECT_SAVE,
#         company_id=company.id,
#         payload={"project_id": p.id},
#     )
#     call_command("process_events", "--once")
#     assert TaskTask.objects.filter(definition__code="TASK-PM-02-01").count() == 1

#     # Удаляем target (эмулируем: пользователь закрыл задачу)
#     TaskTask.objects.filter(definition__code="TASK-PM-02-01").delete()

#     # Повторное событие — source активна, target НЕ создаётся
#     EventBus.publish(
#         PM.PROJECT_SAVE,
#         company_id=company.id,
#         payload={"project_id": p.id},
#     )
#     call_command("process_events", "--once")

#     assert TaskTask.objects.filter(definition__code="TASK-PM-01-01").count() == 1
#     assert TaskTask.objects.filter(definition__code="TASK-PM-02-01").count() == 0


# @pytest.mark.django_db
# def test_transition_not_fired_without_alias(company):
#     """
#     TASK-PM-01-03 (изменение статуса) не имеет transitions →
#     при его событии создаётся только source.
#     """
#     loader = WorkflowLoader(
#         company_id=company.id, module="PM",
#         business_roles_path=WORKFLOW_DIR / "PM_Business_Roles.yml",
#     )
#     loader.load_file(WORKFLOW_DIR / "PM_Process_Workflow.yml")

#     p = Project.objects.create(company=company, code="PROJ-X", name="X")
#     EventBus.publish(
#         "PM.project.updateStatus",
#         company_id=company.id,
#         payload={"project_id": p.id},
#     )
#     call_command("process_events", "--once")

#     assert TaskTask.objects.filter(
#         definition__code="TASK-PM-01-03",
#     ).count() == 1
#     # Никаких target'ов от TASK-PM-01-03 нет


# apps/cp/tests/test_workflow.py (дополнить)
# @pytest.mark.django_db
# def test_transition_counterparty_to_contact(company, cp_type):
#     """
#     CP.counterparty.save → TASK-CP-02-01 (source) +
#     TASK-CP-02-02 (target, добавление контактов).
#     """
#     loader = WorkflowLoader(
#         company_id=company.id, module="CP",
#         business_roles_path=WORKFLOW_DIR / "CP_Business_Roles.yml",
#     )
#     loader.load_file(WORKFLOW_DIR / "CP_Process_Workflow.yml")

#     cp = Counterparty.objects.create(
#         company=company, code="CP-001", name="X",
#         counterparty_type=cp_type,
#     )
#     EventBus.publish(
#         CP.COUNTERPARTY_SAVE,
#         company_id=company.id,
#         payload={"counterparty_id": cp.id, "action": "insert"},
#     )
#     call_command("process_events", "--once")

#     assert TaskTask.objects.filter(
#         company=company, definition__code="TASK-CP-02-01",
#     ).exists()
#     assert TaskTask.objects.filter(
#         company=company, definition__code="TASK-CP-02-02",
#     ).exists()