"""
Модели CRM-модуля. Таблицы — в схеме `crm`.

Соглашения (как в CP):
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (LEAD-001, OPP-001).
- `counterparty_id`, `natural_person_id`, `employee_id`, `material_id`,
  `unit_id` — BigIntegerField (межмодульные ссылки, без FK).
- `created_at`/`updated_at` — из CompanyScopedModel.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# СПРАВОЧНИКИ
# ============================================================

class LeadSource(CompanyScopedModel):
    """Источник лида (сайт, звонок, рекомендация)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'crm"."crm_lead_source'
        verbose_name = _("Lead source")
        verbose_name_plural = _("Lead sources")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_lead_source_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class LeadStatus(CompanyScopedModel):
    """Статус лида (новый, в обработке, квалифицирован, отказ)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'crm"."crm_lead_status'
        verbose_name = _("Lead status")
        verbose_name_plural = _("Lead statuses")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_lead_status_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class OpportunityStage(CompanyScopedModel):
    """Стадия сделки (первичный контакт, переговоры, КП, закрыто)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'crm"."crm_opportunity_stage'
        verbose_name = _("Opportunity stage")
        verbose_name_plural = _("Opportunity stages")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_opportunity_stage_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class ActivityType(CompanyScopedModel):
    """Тип активности (звонок, встреча, письмо)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'crm"."crm_activity_type'
        verbose_name = _("Activity type")
        verbose_name_plural = _("Activity types")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_activity_type_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class SalesFunnel(CompanyScopedModel):
    """Воронка продаж. Этапы хранятся в JSON."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    stages_json = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Stages"),
        help_text=_("Массив этапов: [{'code': ..., 'name': ..., 'order': 1}]"),
    )

    class Meta:
        db_table = 'crm"."crm_sales_funnel'
        verbose_name = _("Sales funnel")
        verbose_name_plural = _("Sales funnels")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_sales_funnel_company_code",
            ),
        ]

    def __str__(self):
        return self.name


# ============================================================
# ЛИДЫ И КОНТАКТЫ
# ============================================================

class Lead(CompanyScopedModel):
    """
    Потенциальный клиент (лид).
    Ссылается на CP через counterparty_id (BigIntegerField, без FK).
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    lead_source = models.ForeignKey(
        LeadSource, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leads", verbose_name=_("Source"),
    )
    lead_status = models.ForeignKey(
        LeadStatus, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="leads", verbose_name=_("Status"),
    )
    # Ссылка на CP.counterparty.id (висячая, без FK)
    counterparty_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Counterparty ID"),
    )
    # Ссылка на hr.hr_employee.id
    responsible_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Responsible employee ID"),
    )
    # Доп. поля, которых нет в схеме, но нужны для работы с лидом
    title = models.CharField(
        max_length=500, blank=True, verbose_name=_("Title"),
        help_text=_("Краткое описание лида"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    contact_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Contact name"),
    )
    contact_phone = models.CharField(
        max_length=50, blank=True, verbose_name=_("Contact phone"),
    )
    contact_email = models.EmailField(
        blank=True, verbose_name=_("Contact email"),
    )

    class Meta:
        db_table = 'crm"."crm_lead'
        verbose_name = _("Lead")
        verbose_name_plural = _("Leads")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_lead_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "lead_status"]),
            models.Index(fields=["company", "responsible_employee_id"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.title or self.contact_name or '—'}"


class Contact(CompanyScopedModel):
    """
    Контактное лицо контрагента (независимая сущность).
    Ссылается на CP.counterparty.id и DICT.natural_person.id.
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    natural_person_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Natural person ID"),
    )
    counterparty_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Counterparty ID"),
    )
    position = models.CharField(
        max_length=255, blank=True, verbose_name=_("Position"),
    )
    phone = models.CharField(max_length=50, blank=True, verbose_name=_("Phone"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))

    class Meta:
        db_table = 'crm"."crm_contact'
        verbose_name = _("Contact")
        verbose_name_plural = _("Contacts")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_contact_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.position or '—'})"


# ============================================================
# СДЕЛКИ
# ============================================================

class Opportunity(CompanyScopedModel):
    """
    Коммерческая возможность (сделка).
    is_won: None — открыта, 1 — выиграна, 0 — проиграна.
    """
    IS_WON_CHOICES = [
        (1, _("Won")),
        (0, _("Lost")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    lead = models.ForeignKey(
        Lead, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="opportunities", verbose_name=_("Lead"),
    )
    opportunity_stage = models.ForeignKey(
        OpportunityStage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="opportunities", verbose_name=_("Stage"),
    )
    responsible_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Responsible employee ID"),
    )
    title = models.CharField(max_length=500, blank=True, verbose_name=_("Title"))
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Amount"),
    )
    expected_close_date = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Expected close date"),
    )
    is_won = models.SmallIntegerField(
        null=True, blank=True, choices=IS_WON_CHOICES,
        db_index=True, verbose_name=_("Is won"),
    )
    lost_reason = models.CharField(
        max_length=500, blank=True, verbose_name=_("Lost reason"),
    )

    class Meta:
        db_table = 'crm"."crm_opportunity'
        verbose_name = _("Opportunity")
        verbose_name_plural = _("Opportunities")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_opportunity_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "opportunity_stage"]),
            models.Index(fields=["company", "is_won"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.title or '—'}"


# ============================================================
# АКТИВНОСТИ
# ============================================================

class Activity(CompanyScopedModel):
    """
    Активность по лиду или сделке.
    Хотя бы одна из ссылок (lead или opportunity) должна быть.
    При удалении лида/сделки — активности удаляются (CASCADE).
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    activity_type = models.ForeignKey(
        ActivityType, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="activities", verbose_name=_("Type"),
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, null=True, blank=True,
        related_name="activities", verbose_name=_("Lead"),
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE, null=True, blank=True,
        related_name="activities", verbose_name=_("Opportunity"),
    )
    employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Employee ID"),
    )
    activity_date = models.DateTimeField(
        db_index=True, verbose_name=_("Activity date"),
    )
    is_completed = models.BooleanField(
        null=True, blank=True, default=False, db_index=True,
        verbose_name=_("Is completed"),
    )
    result = models.TextField(blank=True, verbose_name=_("Result"))
    subject = models.CharField(
        max_length=500, blank=True, verbose_name=_("Subject"),
    )

    class Meta:
        db_table = 'crm"."crm_activity'
        verbose_name = _("Activity")
        verbose_name_plural = _("Activities")
        ordering = ["-activity_date"]
        indexes = [
            models.Index(fields=["company", "is_completed"]),
            models.Index(fields=["company", "activity_date"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_activity_type_display() if self.activity_type else '—'})"


# ============================================================
# КОММЕРЧЕСКИЕ ПРЕДЛОЖЕНИЯ
# ============================================================

class CommercialOffer(CompanyScopedModel):
    """Коммерческое предложение клиенту."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("sent", _("Sent")),
        ("accepted", _("Accepted")),
        ("declined", _("Declined")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.CASCADE,
        related_name="offers", verbose_name=_("Opportunity"),
    )
    offer_date = models.DateField(null=True, blank=True, verbose_name=_("Offer date"))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Total amount"),
    )

    class Meta:
        db_table = 'crm"."crm_commercial_offer'
        verbose_name = _("Commercial offer")
        verbose_name_plural = _("Commercial offers")
        ordering = ["-offer_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_commercial_offer_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"


class CommercialOfferLine(CompanyScopedModel):
    """Позиция КП."""
    id = models.BigAutoField(primary_key=True)
    offer = models.ForeignKey(
        CommercialOffer, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Offer"),
    )
    # Ссылка на crm_price_list_item.id (внутри CRM, но опционально)
    price_list_item = models.ForeignKey(
        "PriceListItem", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="offer_lines", verbose_name=_("Price list item"),
    )
    description = models.CharField(max_length=500, verbose_name=_("Description"))
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    unit_price = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Unit price"),
    )
    line_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Line amount"),
    )

    class Meta:
        db_table = 'crm"."crm_commercial_offer_line'
        verbose_name = _("Commercial offer line")
        verbose_name_plural = _("Commercial offer lines")
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} × {self.quantity}"


# ============================================================
# ПРАЙС-ЛИСТЫ
# ============================================================

class PriceList(CompanyScopedModel):
    """Прайс-лист."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, verbose_name=_("Name"))
    valid_from = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid from"),
    )

    class Meta:
        db_table = 'crm"."crm_price_list'
        verbose_name = _("Price list")
        verbose_name_plural = _("Price lists")
        ordering = ["-valid_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_price_list_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class PriceListItem(CompanyScopedModel):
    """Позиция прайс-листа."""
    ITEM_TYPE_CHOICES = [
        ("material", _("Material")),
        ("service", _("Service")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE,
        related_name="items", verbose_name=_("Price list"),
    )
    item_type = models.CharField(
        max_length=20, choices=ITEM_TYPE_CHOICES, default="material",
        db_index=True, verbose_name=_("Item type"),
    )
    # Ссылка на wms.wms_material.id
    material_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Material ID"),
    )
    service_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Service name"),
    )
    # Ссылка на dict.unit.id
    unit_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Unit ID"),
    )
    price = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Price"),
    )

    class Meta:
        db_table = 'crm"."crm_price_list_item'
        verbose_name = _("Price list item")
        verbose_name_plural = _("Price list items")
        ordering = ["price_list", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_price_list_item_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.price}"


# ============================================================
# ДОГОВОРЫ
# ============================================================

class Contract(CompanyScopedModel):
    """
    Договор с контрагентом.
    covered_objects_json — ссылки на объекты других модулей (заказы, проекты).
    """
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("active", _("Active")),
        ("completed", _("Completed")),
        ("terminated", _("Terminated")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    # Ссылка на CP.counterparty.id
    counterparty_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Counterparty ID"),
    )
    contract_number = models.CharField(
        max_length=100, blank=True, db_index=True,
        verbose_name=_("Contract number"),
    )
    contract_date = models.DateField(
        null=True, blank=True, verbose_name=_("Contract date"),
    )
    contract_amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Contract amount"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    covered_objects_json = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Covered objects"),
        help_text=_("[{'object_type': 'sales_order', 'object_id': 'SO-001'}]"),
    )

    class Meta:
        db_table = 'crm"."crm_contract'
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")
        ordering = ["-contract_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_crm_contract_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "counterparty_id"]),
        ]

    def __str__(self):
        return f"{self.contract_number or self.code} ({self.get_status_display()})"