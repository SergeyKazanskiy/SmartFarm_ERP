"""
Модели HR-модуля. Все таблицы — в схеме `hr`.

Схема задаётся через хак: db_table = 'hr"."hr_position'.
Django сгенерирует SQL: SELECT ... FROM "hr"."hr_position".

Используемые миксины:
- CompanyScopedModel: company + created_at + updated_at

Поля *_id, ссылающиеся на другие модули (natural_person, department,
document, wf_task), оставлены как BigIntegerField без FK — это межмодульные
ссылки, физический FK невозможен между схемами/модулями без циклических
зависимостей.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# РАЗДЕЛ A. СПРАВОЧНИКИ
# ============================================================

class HRPositionCategory(CompanyScopedModel):
    """Категории должностей."""
    id = models.BigAutoField(primary_key=True)
    category_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Category name"),
    )

    class Meta:
        db_table = 'hr"."hr_position_category'
        verbose_name = _("Position category")
        verbose_name_plural = _("Position categories")
        ordering = ["category_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "category_name"],
                name="uq_hr_position_category_company_name",
            ),
        ]

    def __str__(self):
        return self.category_name


class HRPosition(CompanyScopedModel):
    """Должности."""
    id = models.BigAutoField(primary_key=True)
    position_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Position name"),
    )
    category = models.ForeignKey(
        HRPositionCategory,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="positions",
        verbose_name=_("Category"),
    )

    class Meta:
        db_table = 'hr"."hr_position'
        verbose_name = _("Position")
        verbose_name_plural = _("Positions")
        ordering = ["position_name"]

    def __str__(self):
        return self.position_name


class HRWorkSchedule(CompanyScopedModel):
    """Графики работы."""
    TYPE_CHOICES = [
        ("5_2", _("5/2")),
        ("2_2", _("2/2")),
        ("shift", _("Shift work")),
        ("flexible", _("Flexible")),
    ]

    id = models.BigAutoField(primary_key=True)
    schedule_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Schedule name"),
    )
    schedule_type = models.CharField(
        max_length=50, choices=TYPE_CHOICES, blank=True,
        verbose_name=_("Schedule type"),
    )
    weekday_schedule_json = models.JSONField(
        null=True, blank=True,
        verbose_name=_("Weekday schedule"),
        help_text=_("Список: [{'weekday': 'mon', 'start_time': '09:00', 'end_time': '18:00'}]"),
    )

    class Meta:
        db_table = 'hr"."hr_work_schedule'
        verbose_name = _("Work schedule")
        verbose_name_plural = _("Work schedules")
        ordering = ["schedule_name"]

    def __str__(self):
        return self.schedule_name


class HRSkillGroup(CompanyScopedModel):
    """Группы навыков."""
    id = models.BigAutoField(primary_key=True)
    skill_group_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Skill group name"),
    )

    class Meta:
        db_table = 'hr"."hr_skill_group'
        verbose_name = _("Skill group")
        verbose_name_plural = _("Skill groups")
        ordering = ["skill_group_name"]

    def __str__(self):
        return self.skill_group_name


class HRSkill(CompanyScopedModel):
    """Навыки."""
    id = models.BigAutoField(primary_key=True)
    skill_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Skill name"),
    )
    skill_group = models.ForeignKey(
        HRSkillGroup,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="skills",
        verbose_name=_("Skill group"),
    )
    requires_certificate = models.BooleanField(
        default=False,
        verbose_name=_("Requires certificate"),
    )

    class Meta:
        db_table = 'hr"."hr_skill'
        verbose_name = _("Skill")
        verbose_name_plural = _("Skills")
        ordering = ["skill_name"]

    def __str__(self):
        return self.skill_name


class HRQualification(CompanyScopedModel):
    """Квалификации."""
    id = models.BigAutoField(primary_key=True)
    qualification_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Qualification name"),
    )

    class Meta:
        db_table = 'hr"."hr_qualification'
        verbose_name = _("Qualification")
        verbose_name_plural = _("Qualifications")
        ordering = ["qualification_name"]

    def __str__(self):
        return self.qualification_name


class HRCertificate(CompanyScopedModel):
    """Типы сертификатов / допусков."""
    id = models.BigAutoField(primary_key=True)
    certificate_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Certificate name"),
    )
    certificate_type = models.CharField(
        max_length=50, blank=True, verbose_name=_("Certificate type"),
    )

    class Meta:
        db_table = 'hr"."hr_certificate'
        verbose_name = _("Certificate type")
        verbose_name_plural = _("Certificate types")
        ordering = ["certificate_name"]

    def __str__(self):
        return self.certificate_name


class HRAbsenceType(CompanyScopedModel):
    """Типы отсутствий (отпуск, больничный, командировка)."""
    id = models.BigAutoField(primary_key=True)
    absence_type_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Absence type name"),
    )

    class Meta:
        db_table = 'hr"."hr_absence_type'
        verbose_name = _("Absence type")
        verbose_name_plural = _("Absence types")
        ordering = ["absence_type_name"]

    def __str__(self):
        return self.absence_type_name


# ============================================================
# РАЗДЕЛ B. КАДРОВЫЙ УЧЁТ СОТРУДНИКА
# ============================================================

class HREmployee(CompanyScopedModel):
    """
    Сотрудник. Центральная сущность HR-модуля.
    Статусы: candidate_draft → hired → active → on_leave/suspended → dismissed.
    """
    STATUS_CHOICES = [
        ("candidate_draft", _("Candidate draft")),
        ("hired", _("Hired")),
        ("active", _("Active")),
        ("on_leave", _("On leave")),
        ("suspended", _("Suspended")),
        ("dismissed", _("Dismissed")),
    ]

    id = models.BigAutoField(primary_key=True)
    # Ссылка на физлицо из модуля DICT (нет FK — другая схема)
    natural_person_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Natural person ID"),
    )
    personnel_number = models.CharField(
        max_length=50, blank=True, db_index=True,
        verbose_name=_("Personnel number"),
    )
    position = models.ForeignKey(
        HRPosition, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employees", verbose_name=_("Position"),
    )
    # department_id — ссылка на core_department (public)
    department_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Department ID"),
    )
    employment_date = models.DateField(
        null=True, blank=True, verbose_name=_("Employment date"),
    )
    dismissal_date = models.DateField(
        null=True, blank=True, verbose_name=_("Dismissal date"),
    )
    schedule = models.ForeignKey(
        HRWorkSchedule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employees", verbose_name=_("Work schedule"),
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="candidate_draft",
        db_index=True, verbose_name=_("Status"),
    )

    class Meta:
        db_table = 'hr"."hr_employee'
        verbose_name = _("Employee")
        verbose_name_plural = _("Employees")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "personnel_number"],
                condition=models.Q(personnel_number__gt=""),
                name="uq_hr_employee_company_personnel_number",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "department_id"]),
        ]

    def __str__(self):
        return f"{self.personnel_number or self.id} ({self.get_status_display()})"


class HREmployeeDocument(CompanyScopedModel):
    """Кадровые документы (трудовой договор, приказы)."""
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="documents", verbose_name=_("Employee"),
    )
    # document_id — ссылка на doc_document (другой модуль)
    document_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Document ID"),
    )
    document_role = models.CharField(
        max_length=100, blank=True, verbose_name=_("Document role"),
    )

    class Meta:
        db_table = 'hr"."hr_employee_document'
        verbose_name = _("Employee document")
        verbose_name_plural = _("Employee documents")

    def __str__(self):
        return f"Doc {self.document_id} → {self.employee_id}"


# ============================================================
# РАЗДЕЛ C. НАВЫКИ И КОМПЕТЕНЦИИ
# ============================================================

class HREmployeeSkill(CompanyScopedModel):
    """Навыки сотрудника с самооценкой и подтверждением руководителем."""
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="skills", verbose_name=_("Employee"),
    )
    skill = models.ForeignKey(
        HRSkill, on_delete=models.CASCADE,
        related_name="employee_skills", verbose_name=_("Skill"),
    )
    self_assessed_level = models.CharField(
        max_length=50, blank=True, verbose_name=_("Self-assessed level"),
    )
    confirmed_level = models.CharField(
        max_length=50, blank=True, verbose_name=_("Confirmed level"),
    )
    # confirmed_by_employee_id — кто из руководителей подтвердил
    confirmed_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Confirmed by employee ID"),
    )

    class Meta:
        db_table = 'hr"."hr_employee_skill'
        verbose_name = _("Employee skill")
        verbose_name_plural = _("Employee skills")
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "skill"],
                name="uq_hr_employee_skill",
            ),
        ]

    def __str__(self):
        return f"{self.employee_id} — {self.skill_id}"


class HREmployeeCompetencyScore(CompanyScopedModel):
    """Количественная оценка продуктивности по навыку."""
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="competency_scores", verbose_name=_("Employee"),
    )
    skill = models.ForeignKey(
        HRSkill, on_delete=models.CASCADE,
        related_name="competency_scores", verbose_name=_("Skill"),
    )
    score_value = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)],
        verbose_name=_("Score value"),
    )
    evaluated_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Evaluated at"),
    )
    evaluated_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Evaluated by employee ID"),
    )

    class Meta:
        db_table = 'hr"."hr_employee_competency_score'
        verbose_name = _("Competency score")
        verbose_name_plural = _("Competency scores")
        ordering = ["-evaluated_at"]

    def __str__(self):
        return f"{self.employee_id} — {self.skill_id}: {self.score_value}"


class HREmployeeQualification(CompanyScopedModel):
    """Присвоенные сотруднику квалификации."""
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="qualifications", verbose_name=_("Employee"),
    )
    qualification = models.ForeignKey(
        HRQualification, on_delete=models.CASCADE,
        related_name="employee_qualifications", verbose_name=_("Qualification"),
    )
    valid_to = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid to"),
    )

    class Meta:
        db_table = 'hr"."hr_employee_qualification'
        verbose_name = _("Employee qualification")
        verbose_name_plural = _("Employee qualifications")

    def __str__(self):
        return f"{self.employee_id} — {self.qualification_id}"


# ============================================================
# РАЗДЕЛ D. ДОПУСКИ И БЕЗОПАСНОСТЬ
# ============================================================

class HREmployeeCertificate(CompanyScopedModel):
    """Выданные сертификаты и допуски."""
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="certificates", verbose_name=_("Employee"),
    )
    certificate = models.ForeignKey(
        HRCertificate, on_delete=models.CASCADE,
        related_name="employee_certificates", verbose_name=_("Certificate"),
    )
    certificate_number = models.CharField(
        max_length=100, blank=True, verbose_name=_("Certificate number"),
    )
    issue_date = models.DateField(null=True, blank=True, verbose_name=_("Issue date"))
    expire_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Expire date"),
    )

    class Meta:
        db_table = 'hr"."hr_employee_certificate'
        verbose_name = _("Employee certificate")
        verbose_name_plural = _("Employee certificates")
        indexes = [
            models.Index(fields=["company", "expire_date"]),
        ]

    def __str__(self):
        return f"{self.employee_id} — {self.certificate_id}"


class HRMedicalCheck(CompanyScopedModel):
    """Медицинские осмотры."""
    RESULT_CHOICES = [
        ("passed", _("Passed")),
        ("failed", _("Failed")),
        ("conditional", _("Conditional")),
    ]

    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="medical_checks", verbose_name=_("Employee"),
    )
    examination_date = models.DateField(verbose_name=_("Examination date"))
    valid_to = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid to"),
    )
    result = models.CharField(
        max_length=50, choices=RESULT_CHOICES, blank=True,
        verbose_name=_("Result"),
    )

    class Meta:
        db_table = 'hr"."hr_medical_check'
        verbose_name = _("Medical check")
        verbose_name_plural = _("Medical checks")
        ordering = ["-examination_date"]

    def __str__(self):
        return f"{self.employee_id} — {self.examination_date}"


class HRDrivingLicense(CompanyScopedModel):
    """Водительские удостоверения."""
    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="driving_licenses", verbose_name=_("Employee"),
    )
    license_number = models.CharField(max_length=50, verbose_name=_("License number"))
    categories = models.CharField(
        max_length=50, blank=True, verbose_name=_("Categories"),
        help_text="Например: A, B, C, CE",
    )
    valid_to = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid to"),
    )

    class Meta:
        db_table = 'hr"."hr_driving_license'
        verbose_name = _("Driving license")
        verbose_name_plural = _("Driving licenses")

    def __str__(self):
        return f"{self.license_number} ({self.employee_id})"


# ============================================================
# РАЗДЕЛ E. ОТСУТСТВИЯ
# ============================================================

class HREmployeeAbsence(CompanyScopedModel):
    """Заявки на отсутствие (отпуск, больничный, командировка)."""
    STATUS_CHOICES = [
        ("requested", _("Requested")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="absences", verbose_name=_("Employee"),
    )
    absence_type = models.ForeignKey(
        HRAbsenceType, on_delete=models.CASCADE,
        related_name="absences", verbose_name=_("Absence type"),
    )
    date_from = models.DateField(verbose_name=_("Date from"))
    date_to = models.DateField(verbose_name=_("Date to"))
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="requested",
        db_index=True, verbose_name=_("Status"),
    )
    approved_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Approved by employee ID"),
    )

    class Meta:
        db_table = 'hr"."hr_employee_absence'
        verbose_name = _("Employee absence")
        verbose_name_plural = _("Employee absences")
        ordering = ["-date_from"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["employee", "status"]),
        ]

    def __str__(self):
        return f"{self.employee_id} {self.date_from}—{self.date_to} [{self.status}]"


# ============================================================
# РАЗДЕЛ F. ТАБЕЛИРОВАНИЕ
# ============================================================

class HRTimesheet(CompanyScopedModel):
    """Запись табеля учёта рабочего времени."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("submitted", _("Submitted")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
    ]

    id = models.BigAutoField(primary_key=True)
    employee = models.ForeignKey(
        HREmployee, on_delete=models.CASCADE,
        related_name="timesheets", verbose_name=_("Employee"),
    )
    # task_id — ссылка на task.task_task (другой модуль)
    task_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Task ID"),
    )
    work_date = models.DateField(db_index=True, verbose_name=_("Work date"))
    hours_worked = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Hours worked"),
    )
    overtime_hours = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Overtime hours"),
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    approved_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Approved by employee ID"),
    )
    approved_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Approved at"),
    )

    class Meta:
        db_table = 'hr"."hr_timesheet'
        verbose_name = _("Timesheet record")
        verbose_name_plural = _("Timesheet records")
        ordering = ["-work_date"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["employee", "work_date"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "work_date", "task_id"],
                name="uq_hr_timesheet_employee_date_task",
            ),
        ]

    def __str__(self):
        return f"{self.employee_id} {self.work_date}: {self.hours_worked}ч"