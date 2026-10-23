"""
Модели Finance-модуля. Таблицы — в схеме `finance`.

Ключевая особенность: `FinancialTransaction` реализует ПОЛНУЮ двойную запись
(debit_account + credit_account). Любая проводка дебетует один счёт и кредитует
другой — это обязательно для корректного баланса и P&L.

Соглашения (как в CP/CRM/PM/Sales):
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (ACC-001, FINV-001, PAY-001, FT-001).
- Бизнес-номера (invoice_number, account_code, account_number) — отдельные CharField.
- Внешние ссылки (counterparty_id, contract_id, source_object_id, bank_id, currency_id) — BigIntegerField.
- Внутренние FK — ForeignKey с CASCADE/PROTECT/SET_NULL.
- `created_at`/`updated_at` — из CompanyScopedModel.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# СПРАВОЧНИКИ
# ============================================================

class FinAccount(CompanyScopedModel):
    """
    Счёт плана счетов.
    account_type определяет, куда он идёт в отчётности:
    asset/liability → Баланс, income/expense → P&L, equity → Баланс.
    """
    TYPE_CHOICES = [
        ("asset", _("Asset")),
        ("liability", _("Liability")),
        ("equity", _("Equity")),
        ("income", _("Income")),
        ("expense", _("Expense")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    account_code = models.CharField(
        max_length=20, db_index=True, verbose_name=_("Account code"),
        help_text="10, 20, 60, 62, 70, 90…",
    )
    account_name = models.CharField(
        max_length=255, db_index=True, verbose_name=_("Account name"),
    )
    account_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, blank=True,
        db_index=True, verbose_name=_("Account type"),
    )

    class Meta:
        db_table = 'finance"."fin_account'
        verbose_name = _("Account")
        verbose_name_plural = _("Chart of accounts")
        ordering = ["account_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_account_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "account_code"],
                name="uq_fin_account_company_account_code",
            ),
        ]

    def __str__(self):
        return f"{self.account_code} {self.account_name}"


class CostCenter(CompanyScopedModel):
    """Центр затрат."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'finance"."fin_cost_center'
        verbose_name = _("Cost center")
        verbose_name_plural = _("Cost centers")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_cost_center_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class FinancialProject(CompanyScopedModel):
    """
    Финансовый проект — управленческий контур для группировки затрат/выручки
    по проектам других модулей (PROD, PM, Construction).
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))
    linked_object_type = models.CharField(
        max_length=50, blank=True, db_index=True,
        verbose_name=_("Linked object type"),
        help_text="production / project / construction …",
    )
    linked_object_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Linked object ID"),
    )

    class Meta:
        db_table = 'finance"."fin_financial_project'
        verbose_name = _("Financial project")
        verbose_name_plural = _("Financial projects")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_financial_project_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class CashAccount(CompanyScopedModel):
    """Касса."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'finance"."fin_cash_account'
        verbose_name = _("Cash account")
        verbose_name_plural = _("Cash accounts")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_cash_account_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class BankAccount(CompanyScopedModel):
    """Банковский счёт предприятия."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    bank_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Bank ID"),
    )
    account_number = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Account number"),
    )
    currency_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Currency ID"),
    )

    class Meta:
        db_table = 'finance"."fin_bank_account'
        verbose_name = _("Bank account")
        verbose_name_plural = _("Bank accounts")
        ordering = ["account_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_bank_account_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "account_number"],
                name="uq_fin_bank_account_company_number",
            ),
        ]

    def __str__(self):
        return self.account_number


class ExchangeRate(CompanyScopedModel):
    """Курс валюты на дату."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    currency_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Currency ID"),
    )
    rate_date = models.DateField(db_index=True, verbose_name=_("Rate date"))
    rate_value = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Rate value"),
    )

    class Meta:
        db_table = 'finance"."fin_exchange_rate'
        verbose_name = _("Exchange rate")
        verbose_name_plural = _("Exchange rates")
        ordering = ["-rate_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_exchange_rate_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "currency_id", "rate_date"],
                name="uq_fin_exchange_rate_currency_date",
            ),
        ]

    def __str__(self):
        return f"{self.currency_id} @ {self.rate_date}: {self.rate_value}"


# ============================================================
# БЮДЖЕТЫ
# ============================================================

class Budget(CompanyScopedModel):
    """Бюджет на период (может быть привязан к финансовому проекту)."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("approved", _("Approved")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    financial_project = models.ForeignKey(
        FinancialProject, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="budgets", verbose_name=_("Financial project"),
    )
    period_from = models.DateField(db_index=True, verbose_name=_("Period from"))
    period_to = models.DateField(db_index=True, verbose_name=_("Period to"))
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
        db_table = 'finance"."fin_budget'
        verbose_name = _("Budget")
        verbose_name_plural = _("Budgets")
        ordering = ["-period_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_budget_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.period_from} — {self.period_to})"


class BudgetItem(CompanyScopedModel):
    """Статья бюджета по центру затрат."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    budget = models.ForeignKey(
        Budget, on_delete=models.CASCADE,
        related_name="items", verbose_name=_("Budget"),
    )
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.PROTECT, null=True, blank=True,
        related_name="budget_items", verbose_name=_("Cost center"),
    )
    planned_amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name=_("Planned amount"),
    )

    class Meta:
        db_table = 'finance"."fin_budget_item'
        verbose_name = _("Budget item")
        verbose_name_plural = _("Budget items")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_budget_item_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.planned_amount}"


# ============================================================
# СЧЕТА
# ============================================================

class Invoice(CompanyScopedModel):
    """
    Универсальный счёт (AR/AP) на основании документа-основания
    любого модуля (sales_order, procurement_order, construction_act_kb2v и т.д.).
    """
    TYPE_CHOICES = [
        ("AR", _("Accounts Receivable")),
        ("AP", _("Accounts Payable")),
    ]
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("issued", _("Issued")),
        ("partially_paid", _("Partially paid")),
        ("paid", _("Paid")),
        ("overdue", _("Overdue")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    invoice_type = models.CharField(
        max_length=10, choices=TYPE_CHOICES,
        db_index=True, verbose_name=_("Invoice type"),
    )
    counterparty_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Counterparty ID"),
    )
    contract_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Contract ID"),
    )
    source_object_type = models.CharField(
        max_length=50, blank=True, db_index=True,
        verbose_name=_("Source object type"),
        help_text="sales_order, procurement_order, construction_act_kb2v …",
    )
    source_object_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Source object ID"),
    )
    invoice_number = models.CharField(
        max_length=100, blank=True, db_index=True,
        verbose_name=_("Invoice number"),
    )
    invoice_date = models.DateField(db_index=True, verbose_name=_("Invoice date"))
    due_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Due date"),
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name=_("Amount"),
    )
    currency_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Currency ID"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )

    class Meta:
        db_table = 'finance"."fin_invoice'
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ["-invoice_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_invoice_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "invoice_type", "status"]),
            models.Index(fields=["company", "counterparty_id"]),
            models.Index(fields=["source_object_type", "source_object_id"]),
        ]

    def __str__(self):
        return f"{self.invoice_number or self.code} ({self.get_invoice_type_display()})"


class InvoiceLine(CompanyScopedModel):
    """Позиция счёта."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Invoice"),
    )
    description = models.CharField(max_length=500, verbose_name=_("Description"))
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name=_("Amount"),
    )

    class Meta:
        db_table = 'finance"."fin_invoice_line'
        verbose_name = _("Invoice line")
        verbose_name_plural = _("Invoice lines")
        ordering = ["invoice", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_invoice_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.description}: {self.amount}"


# ============================================================
# ПЛАТЕЖИ
# ============================================================

class Payment(CompanyScopedModel):
    """Фактический платёж (поступление или выплата)."""
    STATUS_CHOICES = [
        ("planned", _("Planned")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    invoice = models.ForeignKey(
        Invoice, on_delete=models.PROTECT, null=True, blank=True,
        related_name="payments", verbose_name=_("Invoice"),
    )
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.PROTECT, null=True, blank=True,
        related_name="payments", verbose_name=_("Bank account"),
    )
    cash_account = models.ForeignKey(
        CashAccount, on_delete=models.PROTECT, null=True, blank=True,
        related_name="payments", verbose_name=_("Cash account"),
    )
    payment_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planned",
        db_index=True, verbose_name=_("Status"),
    )
    payment_date = models.DateTimeField(
        db_index=True, verbose_name=_("Payment date"),
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name=_("Amount"),
    )

    class Meta:
        db_table = 'finance"."fin_payment'
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-payment_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_payment_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "payment_status"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.amount} ({self.get_payment_status_display()})"


# ============================================================
# БУХГАЛТЕРСКИЕ ПРОВОДКИ
# ============================================================

class FinancialTransaction(CompanyScopedModel):
    """
    Проводка двойной записи: debit_account = credit_account по сумме.
    Любая хозяйственная операция (платёж, реализация, амортизация)
    представляется одной или несколькими проводками.
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    debit_account = models.ForeignKey(
        FinAccount, on_delete=models.PROTECT,
        related_name="debit_transactions", verbose_name=_("Debit account"),
    )
    credit_account = models.ForeignKey(
        FinAccount, on_delete=models.PROTECT,
        related_name="credit_transactions", verbose_name=_("Credit account"),
    )
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.PROTECT, null=True, blank=True,
        related_name="transactions", verbose_name=_("Cost center"),
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, null=True, blank=True,
        related_name="transactions", verbose_name=_("Payment"),
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name=_("Amount"),
    )
    transaction_date = models.DateTimeField(
        db_index=True, verbose_name=_("Transaction date"),
    )

    class Meta:
        db_table = 'finance"."fin_financial_transaction'
        verbose_name = _("Financial transaction")
        verbose_name_plural = _("Financial transactions")
        ordering = ["-transaction_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_financial_transaction_company_code",
            ),
            models.CheckConstraint(
                check=~models.Q(debit_account=models.F("credit_account")),
                name="ck_fin_tx_debit_ne_credit",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "transaction_date"]),
        ]

    def __str__(self):
        return f"{self.code}: Дт {self.debit_account_id} Кт {self.credit_account_id} = {self.amount}"


# ============================================================
# ПЕРИОДЫ И ПОКАЗАТЕЛИ
# ============================================================

class FinancialPeriod(CompanyScopedModel):
    """Отчётный период. Закрытый период нельзя перепроводить."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=100, verbose_name=_("Period name"))
    date_from = models.DateField(db_index=True, verbose_name=_("Date from"))
    date_to = models.DateField(db_index=True, verbose_name=_("Date to"))
    is_closed = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Is closed"),
    )

    class Meta:
        db_table = 'finance"."fin_financial_period'
        verbose_name = _("Financial period")
        verbose_name_plural = _("Financial periods")
        ordering = ["-date_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_financial_period_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class FinancialIndicator(CompanyScopedModel):
    """Рассчитанный финансовый показатель (revenue, cost_of_goods_sold, ebitda…)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    financial_project = models.ForeignKey(
        FinancialProject, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="indicators", verbose_name=_("Financial project"),
    )
    period = models.ForeignKey(
        FinancialPeriod, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="indicators", verbose_name=_("Period"),
    )
    indicator_code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Indicator code"),
        help_text="revenue, cost_of_goods_sold, ebitda …",
    )
    indicator_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True,
        verbose_name=_("Indicator value"),
    )

    class Meta:
        db_table = 'finance"."fin_financial_indicator'
        verbose_name = _("Financial indicator")
        verbose_name_plural = _("Financial indicators")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_fin_financial_indicator_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.indicator_code}: {self.indicator_value}"