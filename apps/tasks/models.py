"""
Модели TASK-модуля. Все таблицы — в схеме `task`.

Содержит:
1. Runtime-модели задач (TaskTask, TaskAssignment, ...).
2. Workflow-модели (ProcessTaskDefinition, ProcessTaskTransition) —
   загруженные из YAML определения процессов.
"""
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# WORKFLOW-МОДЕЛИ (декларативные определения из YAML)
# ============================================================

class ProcessTaskDefinition(CompanyScopedModel):
    """
    Определение задачи из workflow-YAML.
    Одна запись = один блок `task` в HR_Process_Workflow.yml.

    Пример: TASK-HR-02-06 "Прикрепление кадрового документа",
    role=hr_specialist, on_events=["HR.employee.hire"].
    """
    id = models.BigAutoField(primary_key=True)
    # Модуль: "HR", "TASK", "FIN" — для группировки
    module = models.CharField(max_length=50, db_index=True, verbose_name=_("Module"))
    # ID процесса: "HR-02"
    process_code = models.CharField(max_length=50, db_index=True, verbose_name=_("Process code"))
    # ID задачи: "TASK-HR-02-06"
    code = models.CharField(max_length=100, db_index=True, verbose_name=_("Task code"))
    name = models.CharField(max_length=255, verbose_name=_("Task name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    # Роль, которая должна выполнить задачу: hr_specialist, department_head, ...
    role = models.CharField(max_length=100, db_index=True, verbose_name=_("Role"))
    # Ссылки на операции формы: ["OP-HR-18"]
    form_refs = models.JSONField(default=list, verbose_name=_("Form refs"))
    # События, при которых задача должна создаваться: ["HR.employee.hire"]
    # Именно по этому полю handlers находят определения.

    # ???
    # on_events = models.JSONField(
    #     default=list, db_index=True,
    #     verbose_name=_("Trigger events"),
    #     help_text=_("Список event_type, при которых создаётся задача"),
    # )

    from django.contrib.postgres.fields import ArrayField
    # События, при которых создаётся задача (реальные event_type)
    on_events = ArrayField(
        models.CharField(max_length=128),
        default=list, blank=True,
        db_index=True,
        verbose_name=_("Trigger events"),
        help_text=_("Список event_type, при которых создаётся задача"),
    )
    # Соответствие on_* → event_type (для отладки и UI)
    event_aliases = models.JSONField(
        default=dict, blank=True,
        verbose_name=_("Event aliases"),
        help_text=_("Например {on_insert: 'CP.counterparty.save'}"),
    )


    # SQL-запросы операции: {"on_attach": "OP-HR-18"}
    sql_queries = models.JSONField(default=dict, verbose_name=_("SQL queries"))
    # Порядок для сортировки в UI
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = 'task"."process_task_definition'
        verbose_name = _("Process task definition")
        verbose_name_plural = _("Process task definitions")
        ordering = ["module", "process_code", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_task_definition_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "role", "is_active"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProcessTaskTransition(CompanyScopedModel):
    """
    Переход между задачами из workflow-YAML.
    Описывает: после завершения задачи X при событии Y создаётся задача Z.
    """
    id = models.BigAutoField(primary_key=True)
    source = models.ForeignKey(
        ProcessTaskDefinition, on_delete=models.CASCADE,
        related_name="transitions_out", verbose_name=_("Source"),
    )
    target = models.ForeignKey(
        ProcessTaskDefinition, on_delete=models.CASCADE,
        related_name="transitions_in", verbose_name=_("Target"),
    )
    condition = models.TextField(blank=True, verbose_name=_("Condition"))
    # События, триггерящие переход: ["on_complete", "on_approve"]
    on_events = models.JSONField(default=list, verbose_name=_("On events"))

    class Meta:
        db_table = 'task"."process_task_transition'
        verbose_name = _("Process task transition")
        verbose_name_plural = _("Process task transitions")

    def __str__(self):
        return f"{self.source.code} → {self.target.code}"


# ============================================================
# RUNTIME-МОДЕЛИ ЗАДАЧ (перевод из SQLAlchemy)
# ============================================================

class TaskTask(CompanyScopedModel):
    """Задача — конкретный экземпляр, созданный по определению из workflow."""
    STATUS_CHOICES = [
        ("created", _("Created")),
        ("assigned", _("Assigned")),
        ("in_progress", _("In progress")),
        ("on_hold", _("On hold")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]
    SOURCE_TYPE_CHOICES = [
        ("manual", _("Manual")),
        ("aps", _("APS")),
        ("pm", _("PM")),
        ("hr", _("HR")),
    ]

    id = models.BigAutoField(primary_key=True)
    # Ссылка на определение (если задача создана из workflow)
    definition = models.ForeignKey(
        ProcessTaskDefinition, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tasks", verbose_name=_("Definition"),
    )
    source_type = models.CharField(
        max_length=50, choices=SOURCE_TYPE_CHOICES, default="manual",
        db_index=True, verbose_name=_("Source type"),
    )
    # source_id — ID сущности в источнике (например, employee_id)
    source_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Source ID"),
    )
    # project_id — ссылка на pm_project (другой модуль)
    project_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Project ID"),
    )
    task_name = models.CharField(max_length=255, db_index=True, verbose_name=_("Task name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    planned_start = models.DateTimeField(null=True, blank=True, verbose_name=_("Planned start"))
    planned_finish = models.DateTimeField(null=True, blank=True, verbose_name=_("Planned finish"))
    actual_start = models.DateTimeField(null=True, blank=True, verbose_name=_("Actual start"))
    actual_finish = models.DateTimeField(null=True, blank=True, verbose_name=_("Actual finish"))
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="created",
        db_index=True, verbose_name=_("Status"),
    )
    completion_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Completion %"),
    )
    priority = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("Priority"),
        help_text="1 — самый высокий",
    )
    work_type = models.CharField(max_length=100, blank=True, verbose_name=_("Work type"))
    estimated_hours = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Estimated hours"),
    )
    actual_hours = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Actual hours"),
    )
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )
    # Роль, которая должна выполнить задачу (если ещё не назначен конкретный)
    assigned_role = models.CharField(
        max_length=100, blank=True, db_index=True, verbose_name=_("Assigned role"),
    )

    class Meta:
        db_table = 'task"."task_task'
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "assigned_role", "status"]),
            models.Index(fields=["source_type", "source_id"]),
        ]

    def __str__(self):
        return f"{self.task_name} [{self.status}]"


class TaskAssignment(CompanyScopedModel):
    """Поручение задачи конкретному сотруднику."""
    STATUS_CHOICES = [
        ("assigned", _("Assigned")),
        ("in_progress", _("In progress")),
        ("completed", _("Completed")),
        ("rejected", _("Rejected")),
    ]

    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="assignments", verbose_name=_("Task"),
    )
    employee_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Employee ID"),
    )
    role_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Role ID"),
    )
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Assigned at"))
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="assigned",
        db_index=True, verbose_name=_("Status"),
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Started at"))
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Finished at"))
    assigned_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Assigned by employee ID"),
    )

    class Meta:
        db_table = 'task"."task_assignment'
        verbose_name = _("Task assignment")
        verbose_name_plural = _("Task assignments")
        indexes = [
            models.Index(fields=["employee_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "employee_id"],
                name="uq_task_assignment_task_employee",
            ),
        ]

    def __str__(self):
        return f"Task {self.task_id} → Employee {self.employee_id}"


class TaskStatusHistory(CompanyScopedModel):
    """История изменения статусов задачи."""
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="status_history", verbose_name=_("Task"),
    )
    status_from = models.CharField(max_length=50, blank=True, verbose_name=_("From"))
    status_to = models.CharField(max_length=50, verbose_name=_("To"))
    changed_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Changed by employee ID"),
    )
    comment = models.TextField(blank=True, verbose_name=_("Comment"))

    class Meta:
        db_table = 'task"."task_status_history'
        verbose_name = _("Task status history")
        verbose_name_plural = _("Task status history")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.task_id}: {self.status_from} → {self.status_to}"


class TaskComment(CompanyScopedModel):
    """Комментарии к задаче."""
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="comments", verbose_name=_("Task"),
    )
    employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Employee ID"),
    )
    comment_text = models.TextField(verbose_name=_("Comment"))

    class Meta:
        db_table = 'task"."task_comment'
        verbose_name = _("Task comment")
        verbose_name_plural = _("Task comments")
        ordering = ["created_at"]


class TaskPhoto(CompanyScopedModel):
    """Фотоотчёты по задаче."""
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="photos", verbose_name=_("Task"),
    )
    employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Employee ID"),
    )
    photo = models.ImageField(upload_to="task_photos/%Y/%m/", verbose_name=_("Photo"))
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = 'task"."task_photo'
        verbose_name = _("Task photo")
        verbose_name_plural = _("Task photos")
        ordering = ["-created_at"]


class TaskTimeTracking(CompanyScopedModel):
    """Учёт времени по задаче."""
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="time_tracking", verbose_name=_("Task"),
    )
    employee_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Employee ID"),
    )
    date_logged = models.DateField(db_index=True, verbose_name=_("Date"))
    hours = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name=_("Hours"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = 'task"."task_time_tracking'
        verbose_name = _("Task time tracking")
        verbose_name_plural = _("Task time tracking")
        ordering = ["-date_logged"]
        indexes = [
            models.Index(fields=["employee_id", "date_logged"]),
        ]


class TaskNotification(CompanyScopedModel):
    """Уведомления исполнителям."""
    TYPE_CHOICES = [
        ("assigned", _("Assigned")),
        ("overdue", _("Overdue")),
        ("status_change", _("Status change")),
        ("comment", _("New comment")),
    ]

    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="notifications", verbose_name=_("Task"),
    )
    employee_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Employee ID"),
    )
    notification_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, verbose_name=_("Notification type"),
    )
    message = models.TextField(verbose_name=_("Message"))
    is_read = models.BooleanField(default=False, db_index=True, verbose_name=_("Is read"))
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Sent at"))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Read at"))

    class Meta:
        db_table = 'task"."task_notification'
        verbose_name = _("Task notification")
        verbose_name_plural = _("Task notifications")
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["employee_id", "is_read"]),
        ]


class TaskAttachment(CompanyScopedModel):
    """Прикреплённые к задаче документы."""
    id = models.BigAutoField(primary_key=True)
    task = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="attachments", verbose_name=_("Task"),
    )
    # document_id — ссылка на doc_document (другой модуль)
    document_id = models.BigIntegerField(db_index=True, verbose_name=_("Document ID"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'task"."task_attachment'
        verbose_name = _("Task attachment")
        verbose_name_plural = _("Task attachments")


class TaskDependency(CompanyScopedModel):
    """Зависимости между задачами (для диаграмм Ганта)."""
    TYPE_CHOICES = [
        ("FS", _("Finish → Start")),
        ("SS", _("Start → Start")),
        ("FF", _("Finish → Finish")),
        ("SF", _("Start → Finish")),
    ]

    id = models.BigAutoField(primary_key=True)
    predecessor = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="dependencies_out", verbose_name=_("Predecessor"),
    )
    successor = models.ForeignKey(
        TaskTask, on_delete=models.CASCADE,
        related_name="dependencies_in", verbose_name=_("Successor"),
    )
    dependency_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES, default="FS", verbose_name=_("Type"),
    )
    lag_days = models.IntegerField(default=0, verbose_name=_("Lag (days)"))

    class Meta:
        db_table = 'task"."task_dependency'
        verbose_name = _("Task dependency")
        verbose_name_plural = _("Task dependencies")
        constraints = [
            models.UniqueConstraint(
                fields=["predecessor", "successor"],
                name="uq_task_dependency_pair",
            ),
        ]