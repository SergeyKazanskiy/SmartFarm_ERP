"""
Модели Sales-модуля. Таблицы — в схеме `sales`.

Соглашения (как в CP/CRM/PM):
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (CUST-001, OPP-001, SO-001, PL-001).
- Бизнес-номера (quote_number, order_number, invoice_number, …) — отдельные CharField.
- Внешние ссылки (counterparty_id, hr_employee, wms_material, dict_*) — BigIntegerField.
- Внутренние FK — стандартные ForeignKey с CASCADE / SET_NULL.
- `created_at`/`updated_at` — из CompanyScopedModel (у всех моделей).
"""
from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# СПРАВОЧНИКИ
# ============================================================

class Customer(CompanyScopedModel):
    """
    Клиент (контрагент с коммерческими параметрами).
    Ссылается на CP.counterparty через BigIntegerField (разные схемы).
    """
    CATEGORY_CHOICES = [
        ("VIP", _("VIP")),
        ("regular", _("Regular")),
        ("wholesale", _("Wholesale")),
        ("retail", _("Retail")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    counterparty_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Counterparty ID"),
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, blank=True,
        db_index=True, verbose_name=_("Category"),
    )
    credit_limit = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Credit limit"),
    )
    payment_terms = models.CharField(
        max_length=50, blank=True, verbose_name=_("Payment terms"),
        help_text="net30, prepayment и т.д.",
    )
    default_price_list = models.ForeignKey(
        "PriceList", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="default_for_customers",
        verbose_name=_("Default price list"),
    )
    sales_manager_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Sales manager employee ID"),
    )
    is_active = models.BooleanField(
        default=True, db_index=True, verbose_name=_("Active"),
    )

    class Meta:
        db_table = 'sales"."sales_customer'
        verbose_name = _("Customer")
        verbose_name_plural = _("Customers")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_customer_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "counterparty_id"],
                name="uq_sales_customer_company_counterparty",
            ),
        ]

    def __str__(self):
        return f"{self.code} (CP: {self.counterparty_id})"


class PriceList(CompanyScopedModel):
    """Прайс-лист."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))
    currency_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Currency ID"),
    )
    valid_from = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid from"),
    )
    valid_to = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Valid to"),
    )
    is_default = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Is default"),
    )

    class Meta:
        db_table = 'sales"."sales_price_list'
        verbose_name = _("Price list")
        verbose_name_plural = _("Price lists")
        ordering = ["-valid_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_price_list_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class PriceListLine(CompanyScopedModel):
    """Позиция прайс-листа."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Price list"),
    )
    material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Material ID"),
    )
    unit_price = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Unit price"),
    )
    min_quantity = models.DecimalField(
        max_digits=15, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Min quantity"),
    )

    class Meta:
        db_table = 'sales"."sales_price_list_line'
        verbose_name = _("Price list line")
        verbose_name_plural = _("Price list lines")
        ordering = ["price_list", "material_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_price_list_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.unit_price}"


# ============================================================
# ВОРОНКА ПРОДАЖ
# ============================================================

class Opportunity(CompanyScopedModel):
    """
    Возможность (сделка) в воронке продаж Sales.
    Отличается от CRM.Opportunity: это Sales-версия, со своей стадией и probability.
    """
    STAGE_CHOICES = [
        ("lead", _("Lead")),
        ("negotiation", _("Negotiation")),
        ("proposal", _("Proposal")),
        ("closed_won", _("Closed won")),
        ("closed_lost", _("Closed lost")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="opportunities", verbose_name=_("Customer"),
    )
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Name"))
    stage = models.CharField(
        max_length=20, choices=STAGE_CHOICES, default="lead",
        db_index=True, verbose_name=_("Stage"),
    )
    expected_value = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Expected value"),
    )
    probability_percent = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Probability %"),
    )
    expected_close_date = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Expected close date"),
    )
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'sales"."sales_opportunity'
        verbose_name = _("Opportunity")
        verbose_name_plural = _("Opportunities")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_opportunity_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "stage"]),
        ]

    def __str__(self):
        return f"{self.code} {self.name}"


# ============================================================
# КОММЕРЧЕСКИЕ ПРЕДЛОЖЕНИЯ
# ============================================================

class Quote(CompanyScopedModel):
    """Коммерческое предложение клиенту."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("sent", _("Sent")),
        ("accepted", _("Accepted")),
        ("rejected", _("Rejected")),
        ("expired", _("Expired")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    quote_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Quote number"),
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name="quotes", verbose_name=_("Customer"),
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="quotes", verbose_name=_("Opportunity"),
    )
    quote_date = models.DateField(db_index=True, verbose_name=_("Quote date"))
    valid_until = models.DateField(
        null=True, blank=True, verbose_name=_("Valid until"),
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Total amount"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'sales"."sales_quote'
        verbose_name = _("Quote")
        verbose_name_plural = _("Quotes")
        ordering = ["-quote_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_quote_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.quote_number} ({self.get_status_display()})"


class QuoteLine(CompanyScopedModel):
    """Позиция КП. total_price = quantity × unit_price × (1 − discount/100)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    quote = models.ForeignKey(
        Quote, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Quote"),
    )
    material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Material ID"),
    )
    price_list_item = models.ForeignKey(
        PriceListLine, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="quote_lines", verbose_name=_("Price list item"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    unit_price = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Unit price"),
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Discount %"),
    )
    total_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Total price"),
    )

    class Meta:
        db_table = 'sales"."sales_quote_line'
        verbose_name = _("Quote line")
        verbose_name_plural = _("Quote lines")
        ordering = ["quote", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_quote_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity} × {self.unit_price}"


# ============================================================
# ЗАКАЗЫ
# ============================================================

class Order(CompanyScopedModel):
    """Заказ клиента."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("confirmed", _("Confirmed")),
        ("in_production", _("In production")),
        ("ready_to_ship", _("Ready to ship")),
        ("partially_shipped", _("Partially shipped")),
        ("shipped", _("Shipped")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]
    TYPE_CHOICES = [
        ("regular", _("Regular")),
        ("urgent", _("Urgent")),
        ("sample", _("Sample")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    order_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Order number"),
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT,
        related_name="orders", verbose_name=_("Customer"),
    )
    quote = models.ForeignKey(
        Quote, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="orders", verbose_name=_("Quote"),
    )
    order_date = models.DateField(db_index=True, verbose_name=_("Order date"))
    order_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default="regular",
        verbose_name=_("Order type"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Total amount"),
    )
    currency_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Currency ID"),
    )
    expected_ship_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Expected ship date"),
    )
    actual_ship_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual ship date"),
    )
    delivery_address_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Delivery address ID"),
    )
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )
    production_order_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Production order ID"),
    )

    class Meta:
        db_table = 'sales"."sales_order'
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        ordering = ["-order_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_order_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "customer"]),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()})"


class OrderLine(CompanyScopedModel):
    """Позиция заказа."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Order"),
    )
    material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Material ID"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    unit_price = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Unit price"),
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_("Discount %"),
    )
    total_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Total price"),
    )
    shipped_quantity = models.DecimalField(
        max_digits=15, decimal_places=6, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Shipped quantity"),
    )

    class Meta:
        db_table = 'sales"."sales_order_line'
        verbose_name = _("Order line")
        verbose_name_plural = _("Order lines")
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_order_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity} × {self.unit_price}"


# ============================================================
# ОТГРУЗКИ
# ============================================================

class Shipment(CompanyScopedModel):
    """Отгрузка."""
    STATUS_CHOICES = [
        ("planned", _("Planned")),
        ("in_progress", _("In progress")),
        ("shipped", _("Shipped")),
        ("delivered", _("Delivered")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    shipment_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Shipment number"),
    )
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="shipments", verbose_name=_("Order"),
    )
    warehouse_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Warehouse ID"),
    )
    shipment_date = models.DateField(db_index=True, verbose_name=_("Shipment date"))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planned",
        db_index=True, verbose_name=_("Status"),
    )
    tracking_number = models.CharField(
        max_length=100, blank=True, verbose_name=_("Tracking number"),
    )
    shipping_method_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Shipping method ID"),
    )

    class Meta:
        db_table = 'sales"."sales_shipment'
        verbose_name = _("Shipment")
        verbose_name_plural = _("Shipments")
        ordering = ["-shipment_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_shipment_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.shipment_number} ({self.get_status_display()})"


class ShipmentLine(CompanyScopedModel):
    """Позиция отгрузки."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    shipment = models.ForeignKey(
        Shipment, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Shipment"),
    )
    order_line = models.ForeignKey(
        OrderLine, on_delete=models.CASCADE,
        related_name="shipment_lines", verbose_name=_("Order line"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )

    class Meta:
        db_table = 'sales"."sales_shipment_line'
        verbose_name = _("Shipment line")
        verbose_name_plural = _("Shipment lines")
        ordering = ["shipment", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_shipment_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity}"


# ============================================================
# ВОЗВРАТЫ
# ============================================================

class Return(CompanyScopedModel):
    """Возврат товара от клиента."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("approved", _("Approved")),
        ("received", _("Received")),
        ("rejected", _("Rejected")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    return_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Return number"),
    )
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT,
        related_name="returns", verbose_name=_("Order"),
    )
    return_date = models.DateField(db_index=True, verbose_name=_("Return date"))
    reason = models.TextField(blank=True, verbose_name=_("Reason"))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )

    class Meta:
        db_table = 'sales"."sales_return'
        verbose_name = _("Return")
        verbose_name_plural = _("Returns")
        ordering = ["-return_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_return_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.return_number} ({self.get_status_display()})"


class ReturnLine(CompanyScopedModel):
    """Позиция возврата."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    return_ = models.ForeignKey(
        Return, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Return"),
    )
    order_line = models.ForeignKey(
        OrderLine, on_delete=models.CASCADE,
        related_name="return_lines", verbose_name=_("Order line"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )

    class Meta:
        db_table = 'sales"."sales_return_line'
        verbose_name = _("Return line")
        verbose_name_plural = _("Return lines")
        ordering = ["return_", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_return_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity}"


# ============================================================
# СЧЕТА
# ============================================================

class Invoice(CompanyScopedModel):
    """Счёт на оплату клиенту."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("sent", _("Sent")),
        ("paid", _("Paid")),
        ("overdue", _("Overdue")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    invoice_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Invoice number"),
    )
    order = models.ForeignKey(
        Order, on_delete=models.PROTECT,
        related_name="invoices", verbose_name=_("Order"),
    )
    invoice_date = models.DateField(db_index=True, verbose_name=_("Invoice date"))
    due_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Due date"),
    )
    total_amount = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Total amount"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    paid_amount = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Paid amount"),
    )

    class Meta:
        db_table = 'sales"."sales_invoice'
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ["-invoice_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_sales_invoice_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.invoice_number} ({self.get_status_display()})"