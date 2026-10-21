"""
Модели CP-модуля. Таблицы — в схеме `cp`.

Соглашения:
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (CP-001, CAT-001) — unique в пределах компании.
- Внутренние FK (counterparty→contact_person) → Django ForeignKey.
- Внешние ссылки (hr_employee, dict_currency, doc_document) → BigIntegerField.
- `created_at`/`updated_at` — из CompanyScopedModel.
- При удалении контрагента — каскадное удаление дочерних сущностей.
"""
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# СПРАВОЧНИКИ
# ============================================================

class CounterpartyType(CompanyScopedModel):
    """Тип контрагента: клиент, поставщик, подрядчик, партнёр."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=50, db_index=True,
        verbose_name=_("Code"),
        help_text=_("Например CPT-001"),
    )
    name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Type name"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = 'cp"."cp_counterparty_type'
        verbose_name = _("Counterparty type")
        verbose_name_plural = _("Counterparty types")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_counterparty_type_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


class Category(CompanyScopedModel):
    """Категория контрагента для сегментации (VIP, стандарт, проблемный)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Code"),
    )
    name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Category name"),
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name=_("Parent category"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = 'cp"."cp_category'
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_category_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


# ============================================================
# КОНТРАГЕНТ
# ============================================================

class Counterparty(CompanyScopedModel):
    """
    Основная карточка контрагента.
    Статусы: active / inactive / blocked / blacklisted.
    """
    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
        ("blocked", _("Blocked")),
        ("blacklisted", _("Blacklisted")),
    ]

    id = models.BigAutoField(primary_key=True)
    # Системный код: CP-001 (из test_data counterparty_id)
    code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("System code"),
        help_text=_("Например CP-001"),
    )
    # Бизнес-код: CUST-001 (из Schema.json code)
    internal_code = models.CharField(
        max_length=100, blank=True, db_index=True,
        verbose_name=_("Internal code"),
        help_text=_("Внутренний бизнес-код, например CUST-001"),
    )
    counterparty_type = models.ForeignKey(
        CounterpartyType, on_delete=models.PROTECT,
        related_name="counterparties", verbose_name=_("Type"),
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="counterparties", verbose_name=_("Category"),
    )
    name = models.CharField(
        max_length=500, db_index=True, verbose_name=_("Full name"),
    )
    short_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Short name"),
    )
    tax_id = models.CharField(
        max_length=50, blank=True, db_index=True, verbose_name=_("Tax ID"),
    )
    tax_registration_id = models.CharField(
        max_length=50, blank=True, verbose_name=_("Tax registration ID"),
    )
    vat_registration = models.CharField(
        max_length=50, blank=True, verbose_name=_("VAT registration"),
    )
    legal_address = models.TextField(blank=True, verbose_name=_("Legal address"))
    actual_address = models.TextField(blank=True, verbose_name=_("Actual address"))
    phone = models.CharField(max_length=50, blank=True, verbose_name=_("Phone"))
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    website = models.CharField(max_length=255, blank=True, verbose_name=_("Website"))
    industry = models.CharField(
        max_length=255, blank=True, verbose_name=_("Industry"),
    )
    credit_limit = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Credit limit"),
    )
    payment_terms = models.CharField(
        max_length=50, blank=True, verbose_name=_("Payment terms"),
        help_text=_("Например net30, prepayment"),
    )
    delivery_terms = models.CharField(
        max_length=50, blank=True, verbose_name=_("Delivery terms"),
        help_text=_("Например DDP, FOB"),
    )
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default="active",
        db_index=True, verbose_name=_("Status"),
    )
    is_blacklisted = models.BooleanField(
        default=False, db_index=True, verbose_name=_("In blacklist"),
    )
    # Внешние ссылки (схемы hr)
    responsible_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Responsible employee ID"),
    )
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'cp"."cp_counterparty'
        verbose_name = _("Counterparty")
        verbose_name_plural = _("Counterparties")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_counterparty_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "is_blacklisted"]),
            models.Index(fields=["company", "counterparty_type"]),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


# ============================================================
# ДОЧЕРНИЕ СУЩНОСТИ КОНТРАГЕНТА
# (каскадное удаление при удалении контрагента)
# ============================================================

class ContactPerson(CompanyScopedModel):
    """Контактное лицо контрагента."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Code"),
    )
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="contacts", verbose_name=_("Counterparty"),
    )
    # Ссылка на физлицо (модуль DICT)
    natural_person_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Natural person ID"),
    )
    first_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("First name"),
    )
    last_name = models.CharField(
        max_length=255, blank=True, db_index=True, verbose_name=_("Last name"),
    )
    middle_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Middle name"),
    )
    position = models.CharField(
        max_length=255, blank=True, verbose_name=_("Position"),
    )
    department = models.CharField(
        max_length=255, blank=True, verbose_name=_("Department"),
    )
    phone = models.CharField(max_length=50, blank=True, verbose_name=_("Phone"))
    mobile_phone = models.CharField(
        max_length=50, blank=True, verbose_name=_("Mobile phone"),
    )
    email = models.EmailField(blank=True, verbose_name=_("Email"))
    is_primary = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Primary contact"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = 'cp"."cp_contact_person'
        verbose_name = _("Contact person")
        verbose_name_plural = _("Contact persons")
        ordering = ["-is_primary", "last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_contact_person_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.last_name} {self.first_name}".strip() or self.code


class BankAccount(CompanyScopedModel):
    """Банковский счёт контрагента."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Code"),
    )
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="bank_accounts", verbose_name=_("Counterparty"),
    )
    bank_name = models.CharField(
        max_length=255, blank=True, verbose_name=_("Bank name"),
    )
    bank_code = models.CharField(
        max_length=50, blank=True, verbose_name=_("Bank code (MFO/BIC)"),
    )
    account_number = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Account number (IBAN)"),
    )
    # Ссылка на справочник валют (DICT)
    currency_id = models.BigIntegerField(
        null=True, blank=True, db_index=True, verbose_name=_("Currency ID"),
    )
    is_primary = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Primary account"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = 'cp"."cp_bank_account'
        verbose_name = _("Bank account")
        verbose_name_plural = _("Bank accounts")
        ordering = ["-is_primary", "bank_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_bank_account_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.bank_name} {self.account_number[:8]}…"


class Address(CompanyScopedModel):
    """Адрес контрагента."""
    TYPE_CHOICES = [
        ("legal", _("Legal")),
        ("actual", _("Actual")),
        ("warehouse", _("Warehouse")),
        ("delivery", _("Delivery")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Code"),
    )
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="addresses", verbose_name=_("Counterparty"),
    )
    address_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, blank=True,
        db_index=True, verbose_name=_("Address type"),
    )
    address_line1 = models.CharField(
        max_length=500, blank=True, verbose_name=_("Address line 1"),
    )
    address_line2 = models.CharField(
        max_length=500, blank=True, verbose_name=_("Address line 2"),
    )
    city = models.CharField(max_length=255, blank=True, verbose_name=_("City"))
    region = models.CharField(max_length=255, blank=True, verbose_name=_("Region"))
    postal_code = models.CharField(
        max_length=20, blank=True, verbose_name=_("Postal code"),
    )
    # Ссылка на справочник стран (DICT)
    country_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Country ID"),
    )
    is_primary = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Primary address"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        db_table = 'cp"."cp_address'
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        ordering = ["-is_primary", "city"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_address_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.city}, {self.address_line1}".strip(", ") or self.code


class Rating(CompanyScopedModel):
    """
    Оценка контрагента. История: один контрагент — много записей.
    Шкала: 1–10.
    """
    TYPE_CHOICES = [
        ("financial", _("Financial")),
        ("reliability", _("Reliability")),
        ("quality", _("Quality")),
        ("overall", _("Overall")),
    ]

    id = models.BigAutoField(primary_key=True)
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="ratings", verbose_name=_("Counterparty"),
    )
    rating_date = models.DateField(db_index=True, verbose_name=_("Rating date"))
    rating_value = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_("Rating (1-10)"),
    )
    rating_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="overall",
        db_index=True, verbose_name=_("Rating type"),
    )
    comment = models.TextField(blank=True, verbose_name=_("Comment"))
    rated_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Rated by employee ID"),
    )

    class Meta:
        db_table = 'cp"."cp_rating'
        verbose_name = _("Rating")
        verbose_name_plural = _("Ratings")
        ordering = ["-rating_date"]
        indexes = [
            models.Index(fields=["counterparty", "rating_date"]),
        ]

    def __str__(self):
        return f"{self.counterparty_id}: {self.rating_value}/10 ({self.rating_date})"


class Interaction(CompanyScopedModel):
    """Журнал взаимодействий с контрагентом."""
    TYPE_CHOICES = [
        ("call", _("Call")),
        ("meeting", _("Meeting")),
        ("email", _("Email")),
        ("visit", _("Visit")),
        ("complaint", _("Complaint")),
    ]

    id = models.BigAutoField(primary_key=True)
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="interactions", verbose_name=_("Counterparty"),
    )
    interaction_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, db_index=True,
        verbose_name=_("Interaction type"),
    )
    interaction_date = models.DateTimeField(
        db_index=True, verbose_name=_("Interaction date"),
    )
    contact_person = models.ForeignKey(
        ContactPerson, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interactions", verbose_name=_("Contact person"),
    )
    employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Employee ID"),
    )
    subject = models.CharField(max_length=500, blank=True, verbose_name=_("Subject"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    result = models.TextField(blank=True, verbose_name=_("Result"))
    next_action_date = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Next action date"),
    )

    class Meta:
        db_table = 'cp"."cp_interaction'
        verbose_name = _("Interaction")
        verbose_name_plural = _("Interactions")
        ordering = ["-interaction_date"]
        indexes = [
            models.Index(fields=["counterparty", "interaction_date"]),
        ]

    def __str__(self):
        return f"{self.get_interaction_type_display()} — {self.subject or self.id}"


class Contract(CompanyScopedModel):
    """Договор с контрагентом."""
    TYPE_CHOICES = [
        ("sales", _("Sales")),
        ("procurement", _("Procurement")),
        ("service", _("Service")),
        ("partnership", _("Partnership")),
    ]
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("active", _("Active")),
        ("expired", _("Expired")),
        ("terminated", _("Terminated")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Code"),
    )
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="contracts", verbose_name=_("Counterparty"),
    )
    contract_number = models.CharField(
        max_length=100, blank=True, db_index=True,
        verbose_name=_("Contract number"),
    )
    contract_date = models.DateField(
        null=True, blank=True, verbose_name=_("Contract date"),
    )
    valid_from = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid from"),
    )
    valid_to = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid to"),
    )
    contract_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, blank=True,
        db_index=True, verbose_name=_("Contract type"),
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Amount"),
    )
    currency_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Currency ID"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'cp"."cp_contract'
        verbose_name = _("Contract")
        verbose_name_plural = _("Contracts")
        ordering = ["-contract_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_contract_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "valid_to"]),
        ]

    def __str__(self):
        return f"{self.contract_number or self.code} ({self.get_status_display()})"


class Attachment(CompanyScopedModel):
    """Прикреплённый документ контрагента."""
    TYPE_CHOICES = [
        ("registration", _("Registration")),
        ("contract", _("Contract")),
        ("certificate", _("Certificate")),
        ("license", _("License")),
        ("passport", _("Passport")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Code"),
    )
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="attachments", verbose_name=_("Counterparty"),
    )
    # Ссылка на документ (модуль DOC)
    document_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Document ID"),
    )
    attachment_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, blank=True,
        db_index=True, verbose_name=_("Attachment type"),
    )
    description = models.TextField(blank=True, verbose_name=_("Description"))
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'cp"."cp_attachment'
        verbose_name = _("Attachment")
        verbose_name_plural = _("Attachments")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_cp_attachment_company_code",
            ),
        ]

    def __str__(self):
        return f"Doc {self.document_id} ({self.get_attachment_type_display() or '—'})"


class Blacklist(CompanyScopedModel):
    """Запись о блокировке контрагента в чёрном списке."""
    id = models.BigAutoField(primary_key=True)
    counterparty = models.ForeignKey(
        Counterparty, on_delete=models.CASCADE,
        related_name="blacklist_entries", verbose_name=_("Counterparty"),
    )
    block_date = models.DateField(db_index=True, verbose_name=_("Block date"))
    reason = models.TextField(blank=True, verbose_name=_("Reason"))
    blocked_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Blocked by employee ID"),
    )
    unblock_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Unblock date"),
    )
    unblock_reason = models.TextField(blank=True, verbose_name=_("Unblock reason"))
    unblocked_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Unblocked by employee ID"),
    )

    class Meta:
        db_table = 'cp"."cp_blacklist'
        verbose_name = _("Blacklist entry")
        verbose_name_plural = _("Blacklist entries")
        ordering = ["-block_date"]
        indexes = [
            models.Index(fields=["counterparty", "unblock_date"]),
        ]

    def __str__(self):
        status = "разблокирован" if self.unblock_date else "заблокирован"
        return f"{self.counterparty_id} [{status}] с {self.block_date}"