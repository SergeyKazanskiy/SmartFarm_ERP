"""
Модели PM-модуля. Таблицы — в схеме `pm`.

Соглашения (как в CP/CRM):
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (PROJ-001).
- `orchestrator_id` — внешний ID (CharField, из системы Orchestrator).
- `customer_id`, `project_manager_employee_id`, `assignee_employee_id`,
  `owner_employee_id`, `role_id`, `skill_id`, `unit_id`, `currency_id` —
  BigIntegerField (межмодульные ссылки).
- `created_at`/`updated_at` — из CompanyScopedModel.
- Self-ref (parent) — SET_NULL. Остальные FK — CASCADE.
"""
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# ПРОЕКТЫ
# ============================================================

class Project(CompanyScopedModel):
    """
    Основной проект.
    Статусы: planning → active → on_hold → completed / cancelled.
    """
    STATUS_CHOICES = [
        ("planning", _("Planning")),
        ("active", _("Active")),
        ("on_hold", _("On hold")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Project name"))
    project_code = models.CharField(
        max_length=100, blank=True, db_index=True, verbose_name=_("Project code"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    # ID из внешней системы Orchestrator (не FK — другая система)
    orchestrator_id = models.CharField(
        max_length=50, blank=True, db_index=True,
        verbose_name=_("Orchestrator ID"),
    )
    # Ссылка на CP.counterparty.id
    customer_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Customer ID"),
    )
    # Ссылка на hr.hr_employee.id
    project_manager_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Project manager ID"),
    )
    planned_start_date = models.DateField(
        null=True, blank=True, verbose_name=_("Planned start"),
    )
    planned_end_date = models.DateField(
        null=True, blank=True, verbose_name=_("Planned end"),
    )
    actual_start_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual start"),
    )
    actual_end_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual end"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planning",
        db_index=True, verbose_name=_("Status"),
    )
    priority = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("Priority"),
        help_text="1 — самый высокий",
    )
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'pm"."pm_project'
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_project_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "customer_id"]),
            models.Index(fields=["company", "orchestrator_id"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


# ============================================================
# ЭТАПЫ И ВЕХИ
# ============================================================

class Phase(CompanyScopedModel):
    """Этап проекта. Может быть вложенным (parent_phase)."""
    STATUS_CHOICES = [
        ("planned", _("Planned")),
        ("in_progress", _("In progress")),
        ("completed", _("Completed")),
        ("on_hold", _("On hold")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="phases", verbose_name=_("Project"),
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name=_("Parent phase"),
    )
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Phase name"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Order"))
    planned_start_date = models.DateField(
        null=True, blank=True, verbose_name=_("Planned start"),
    )
    planned_end_date = models.DateField(
        null=True, blank=True, verbose_name=_("Planned end"),
    )
    actual_start_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual start"),
    )
    actual_end_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual end"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planned",
        db_index=True, verbose_name=_("Status"),
    )
    completion_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Completion %"),
    )

    class Meta:
        db_table = 'pm"."pm_phase'
        verbose_name = _("Phase")
        verbose_name_plural = _("Phases")
        ordering = ["project", "order"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_phase_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


class Milestone(CompanyScopedModel):
    """Веха проекта."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="milestones", verbose_name=_("Project"),
    )
    name = models.CharField(max_length=500, verbose_name=_("Milestone name"))
    milestone_date = models.DateField(db_index=True, verbose_name=_("Milestone date"))
    is_achieved = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Is achieved"),
    )
    achieved_date = models.DateField(
        null=True, blank=True, verbose_name=_("Achieved date"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = 'pm"."pm_milestone'
        verbose_name = _("Milestone")
        verbose_name_plural = _("Milestones")
        ordering = ["project", "milestone_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_milestone_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


# ============================================================
# ЗАДАЧИ
# ============================================================

class Task(CompanyScopedModel):
    """
    Задача высокого уровня проекта.
    Не путать с task.task_task (TASK-модуль) — это PM-задачи,
    которые при необходимости декомпозируются в TASK.
    """
    STATUS_CHOICES = [
        ("planned", _("Planned")),
        ("in_progress", _("In progress")),
        ("completed", _("Completed")),
        ("on_hold", _("On hold")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="tasks", verbose_name=_("Project"),
    )
    phase = models.ForeignKey(
        Phase, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tasks", verbose_name=_("Phase"),
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="subtasks", verbose_name=_("Parent task"),
    )
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Task name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    planned_start_date = models.DateField(
        null=True, blank=True, verbose_name=_("Planned start"),
    )
    planned_end_date = models.DateField(
        null=True, blank=True, verbose_name=_("Planned end"),
    )
    actual_start_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual start"),
    )
    actual_end_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual end"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planned",
        db_index=True, verbose_name=_("Status"),
    )
    completion_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Completion %"),
    )
    priority = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("Priority"),
    )
    # Ссылка на hr.hr_employee.id
    assignee_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Assignee employee ID"),
    )

    class Meta:
        db_table = 'pm"."pm_task'
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")
        ordering = ["project", "priority", "planned_start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_task_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "assignee_employee_id"]),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


class TaskDependency(CompanyScopedModel):
    """
    Зависимость между задачами.
    Типы: FS (finish→start), SS (start→start), FF (finish→finish), SF (start→finish).
    """
    TYPE_CHOICES = [
        ("FS", _("Finish → Start")),
        ("SS", _("Start → Start")),
        ("FF", _("Finish → Finish")),
        ("SF", _("Start → Finish")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    predecessor = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name="dependencies_out", verbose_name=_("Predecessor"),
    )
    successor = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name="dependencies_in", verbose_name=_("Successor"),
    )
    dependency_type = models.CharField(
        max_length=2, choices=TYPE_CHOICES, default="FS",
        verbose_name=_("Type"),
    )
    lag_days = models.IntegerField(default=0, verbose_name=_("Lag (days)"))

    class Meta:
        db_table = 'pm"."pm_task_dependency'
        verbose_name = _("Task dependency")
        verbose_name_plural = _("Task dependencies")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_task_dependency_company_code",
            ),
            models.UniqueConstraint(
                fields=["predecessor", "successor"],
                name="uq_pm_task_dependency_pair",
            ),
        ]

    def __str__(self):
        return f"{self.predecessor_id} → {self.successor_id} ({self.dependency_type})"


# ============================================================
# РЕСУРСНЫЕ ПОТРЕБНОСТИ
# ============================================================

class ResourceNeed(CompanyScopedModel):
    """
    Потребность в ресурсах. Передаётся в APS.
    До отправки в APS sent_to_aps=False.
    """
    TYPE_CHOICES = [
        ("employee", _("Employee")),
        ("asset", _("Asset")),
        ("vehicle", _("Vehicle")),
        ("material", _("Material")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE,
        related_name="resource_needs", verbose_name=_("Task"),
    )
    resource_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES,
        db_index=True, verbose_name=_("Resource type"),
    )
    # Ссылка на hr.hr_position.id
    role_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Role ID"),
    )
    # Ссылка на hr.hr_skill.id
    skill_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Skill ID"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    # Ссылка на dict.unit.id
    unit_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Unit ID"),
    )
    hours_per_day = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Hours per day"),
    )
    days_required = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Days required"),
    )
    priority = models.PositiveSmallIntegerField(
        null=True, blank=True, verbose_name=_("Priority"),
    )
    sent_to_aps = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Sent to APS"),
    )
    sent_to_aps_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Sent to APS at"),
    )

    class Meta:
        db_table = 'pm"."pm_resource_need'
        verbose_name = _("Resource need")
        verbose_name_plural = _("Resource needs")
        ordering = ["task", "priority"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_resource_need_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.resource_type} × {self.quantity}"


# ============================================================
# БЮДЖЕТ
# ============================================================

class Budget(CompanyScopedModel):
    """Бюджет проекта."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("approved", _("Approved")),
        ("in_progress", _("In progress")),
        ("closed", _("Closed")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="budgets", verbose_name=_("Project"),
    )
    name = models.CharField(max_length=255, blank=True, verbose_name=_("Budget name"))
    total_planned_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Total planned"),
    )
    total_actual_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Total actual"),
    )
    currency_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Currency ID"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    approved_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Approved by employee ID"),
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Approved at"),
    )

    class Meta:
        db_table = 'pm"."pm_budget'
        verbose_name = _("Budget")
        verbose_name_plural = _("Budgets")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_budget_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name or self.project.code}"


class BudgetItem(CompanyScopedModel):
    """Статья бюджета."""
    CATEGORY_CHOICES = [
        ("labor", _("Labor")),
        ("materials", _("Materials")),
        ("equipment", _("Equipment")),
        ("services", _("Services")),
        ("other", _("Other")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    budget = models.ForeignKey(
        Budget, on_delete=models.CASCADE,
        related_name="items", verbose_name=_("Budget"),
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES,
        db_index=True, verbose_name=_("Category"),
    )
    planned_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name=_("Planned amount"),
    )
    actual_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Actual amount"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))

    class Meta:
        db_table = 'pm"."pm_budget_item'
        verbose_name = _("Budget item")
        verbose_name_plural = _("Budget items")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_budget_item_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.planned_amount}"


# ============================================================
# РИСКИ
# ============================================================

class Risk(CompanyScopedModel):
    """Риск проекта. severity = probability × impact (вычисляется в сервисе)."""
    STATUS_CHOICES = [
        ("identified", _("Identified")),
        ("assessed", _("Assessed")),
        ("mitigated", _("Mitigated")),
        ("closed", _("Closed")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="risks", verbose_name=_("Project"),
    )
    name = models.CharField(max_length=500, verbose_name=_("Risk name"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    probability = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Probability (%)"),
    )
    impact = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        verbose_name=_("Impact (1-10)"),
    )
    severity = models.PositiveIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Severity"),
    )
    mitigation_plan = models.TextField(blank=True, verbose_name=_("Mitigation plan"))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="identified",
        db_index=True, verbose_name=_("Status"),
    )
    owner_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Owner employee ID"),
    )

    class Meta:
        db_table = 'pm"."pm_risk'
        verbose_name = _("Risk")
        verbose_name_plural = _("Risks")
        ordering = ["-severity"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_risk_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name} (severity {self.severity or 0})"


# ============================================================
# ЗАПРОСЫ НА ИЗМЕНЕНИЕ
# ============================================================

class ChangeRequest(CompanyScopedModel):
    """Запрос на изменение объёма работ / сроков / бюджета / ресурсов."""
    TYPE_CHOICES = [
        ("scope", _("Scope")),
        ("schedule", _("Schedule")),
        ("budget", _("Budget")),
        ("resources", _("Resources")),
    ]
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("submitted", _("Submitted")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
        ("implemented", _("Implemented")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="change_requests", verbose_name=_("Project"),
    )
    title = models.CharField(max_length=500, verbose_name=_("Title"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    change_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES,
        db_index=True, verbose_name=_("Change type"),
    )
    impact_description = models.TextField(
        blank=True, verbose_name=_("Impact description"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    requested_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Requested by employee ID"),
    )
    approved_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Approved by employee ID"),
    )
    requested_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Requested at"),
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Approved at"),
    )

    class Meta:
        db_table = 'pm"."pm_change_request'
        verbose_name = _("Change request")
        verbose_name_plural = _("Change requests")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_change_request_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.title}"


# ============================================================
# ИСТОРИЯ И ОТЧЁТЫ
# ============================================================

class StatusHistory(CompanyScopedModel):
    """История изменений статуса проекта."""
    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="status_history", verbose_name=_("Project"),
    )
    status_from = models.CharField(
        max_length=20, blank=True, verbose_name=_("From"),
    )
    status_to = models.CharField(max_length=20, verbose_name=_("To"))
    changed_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Changed by employee ID"),
    )
    changed_at = models.DateTimeField(verbose_name=_("Changed at"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))

    class Meta:
        db_table = 'pm"."pm_status_history'
        verbose_name = _("Status history")
        verbose_name_plural = _("Status history")
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.status_from} → {self.status_to} ({self.changed_at})"


class Report(CompanyScopedModel):
    """
    Агрегированный отчёт для Orchestrator.
    Содержит 4 JSON-блока: status_summary, budget_summary, schedule_summary, risks_summary.
    """
    TYPE_CHOICES = [
        ("daily", _("Daily")),
        ("weekly", _("Weekly")),
        ("monthly", _("Monthly")),
        ("milestone", _("Milestone")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE,
        related_name="reports", verbose_name=_("Project"),
    )
    report_date = models.DateTimeField(db_index=True, verbose_name=_("Report date"))
    report_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES,
        db_index=True, verbose_name=_("Report type"),
    )
    summary = models.TextField(blank=True, verbose_name=_("Summary"))
    status_summary_json = models.JSONField(
        default=dict, blank=True, verbose_name=_("Status summary"),
    )
    budget_summary_json = models.JSONField(
        default=dict, blank=True, verbose_name=_("Budget summary"),
    )
    schedule_summary_json = models.JSONField(
        default=dict, blank=True, verbose_name=_("Schedule summary"),
    )
    risks_summary_json = models.JSONField(
        default=dict, blank=True, verbose_name=_("Risks summary"),
    )
    sent_to_orchestrator = models.BooleanField(
        default=False, db_index=True,
        verbose_name=_("Sent to orchestrator"),
    )
    sent_to_orchestrator_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Sent to orchestrator at"),
    )

    class Meta:
        db_table = 'pm"."pm_report'
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ["-report_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_pm_report_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_report_type_display()})"