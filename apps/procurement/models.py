"""
Модели Procurement-модуля. Таблицы — в схеме `procurement`.

Соглашения (как в предыдущих модулях):
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (SUP-001, REQ-001, PO-001).
- Бизнес-номера (requisition_number, rfq_number, order_number) — отдельные CharField.
- Внешние ссылки (counterparty_id, material_id, unit_id, currency_id,
  requested_by_employee_id, created_by_employee_id, changed_by_employee_id) — BigIntegerField.
- Внутренние FK — ForeignKey с CASCADE/PROTECT/SET_NULL.
- `created_at`/`updated_at` — из CompanyScopedModel.
"""
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# ПОСТАВЩИКИ
# ============================================================

class Supplier(CompanyScopedModel):
    """
    Поставщик (контрагент с коммерческими параметрами).
    Один контрагент = один поставщик в рамках компании.
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    counterparty_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Counterparty ID"),
    )
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name=_("Rating (1-10)"),
    )
    payment_terms = models.CharField(
        max_length=50, blank=True, verbose_name=_("Payment terms"),
        help_text="net30, prepayment и т.д.",
    )
    delivery_terms = models.CharField(
        max_length=50, blank=True, verbose_name=_("Delivery terms"),
        help_text="DDP, FOB и т.д.",
    )
    lead_time_days = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Lead time (days)"),
    )
    is_preferred = models.BooleanField(
        default=False, db_index=True, verbose_name=_("Preferred"),
    )

    class Meta:
        db_table = 'procurement"."procurement_supplier'
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ["-is_preferred", "-rating", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_supplier_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "counterparty_id"],
                name="uq_proc_supplier_company_counterparty",
            ),
        ]

    def __str__(self):
        return f"{self.code} (CP: {self.counterparty_id})"


# ============================================================
# ЗАЯВКИ НА ЗАКУПКУ
# ============================================================

class Requisition(CompanyScopedModel):
    """Внутренняя заявка на закупку."""
    SOURCE_TYPE_CHOICES = [
        ("wms_deficit", _("WMS deficit")),
        ("production_need", _("Production need")),
        ("toir_spare_part", _("TOIR spare part")),
        ("manual", _("Manual")),
    ]
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("pending_approval", _("Pending approval")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
        ("ordered", _("Ordered")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    requisition_number = models.CharField(
        max_length=100, db_index=True,
        verbose_name=_("Requisition number"),
    )
    source_type = models.CharField(
        max_length=30, choices=SOURCE_TYPE_CHOICES, default="manual",
        db_index=True, verbose_name=_("Source type"),
    )
    source_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Source ID"),
    )
    requisition_date = models.DateField(
        db_index=True, verbose_name=_("Requisition date"),
    )
    requested_by_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Requested by employee ID"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    planned_order_date = models.DateField(
        null=True, blank=True, verbose_name=_("Planned order date"),
    )
    required_date = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Required date"),
    )

    class Meta:
        db_table = 'procurement"."procurement_requisition'
        verbose_name = _("Requisition")
        verbose_name_plural = _("Requisitions")
        ordering = ["-requisition_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_requisition_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "requisition_number"],
                name="uq_proc_requisition_company_number",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "source_type", "source_id"]),
        ]

    def __str__(self):
        return f"{self.requisition_number} ({self.get_status_display()})"


class RequisitionLine(CompanyScopedModel):
    """Позиция заявки на закупку."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    requisition = models.ForeignKey(
        Requisition, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Requisition"),
    )
    material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Material ID"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    unit_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Unit ID"),
    )
    estimated_unit_cost = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Estimated unit cost"),
    )

    class Meta:
        db_table = 'procurement"."procurement_requisition_line'
        verbose_name = _("Requisition line")
        verbose_name_plural = _("Requisition lines")
        ordering = ["requisition", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_requisition_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity} (material {self.material_id})"


# ============================================================
# ЗАПРОСЫ ПРЕДЛОЖЕНИЙ (RFQ)
# ============================================================

class RFQ(CompanyScopedModel):
    """Запрос ценовых предложений поставщикам."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("sent", _("Sent")),
        ("responded", _("Responded")),
        ("closed", _("Closed")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    rfq_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("RFQ number"),
    )
    requisition = models.ForeignKey(
        Requisition, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="rfqs", verbose_name=_("Requisition"),
    )
    rfq_date = models.DateField(db_index=True, verbose_name=_("RFQ date"))
    response_deadline = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Response deadline"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )

    class Meta:
        db_table = 'procurement"."procurement_rfq'
        verbose_name = _("RFQ")
        verbose_name_plural = _("RFQs")
        ordering = ["-rfq_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_rfq_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "rfq_number"],
                name="uq_proc_rfq_company_number",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.rfq_number} ({self.get_status_display()})"


class RFQSupplier(CompanyScopedModel):
    """Привязка поставщика к RFQ."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    rfq = models.ForeignKey(
        RFQ, on_delete=models.CASCADE,
        related_name="suppliers", verbose_name=_("RFQ"),
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT,
        related_name="rfq_links", verbose_name=_("Supplier"),
    )

    class Meta:
        db_table = 'procurement"."procurement_rfq_supplier'
        verbose_name = _("RFQ supplier")
        verbose_name_plural = _("RFQ suppliers")
        ordering = ["rfq", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_rfq_supplier_company_code",
            ),
            models.UniqueConstraint(
                fields=["rfq", "supplier"],
                name="uq_proc_rfq_supplier_pair",
            ),
        ]

    def __str__(self):
        return f"{self.rfq.rfq_number} → {self.supplier.code}"


class SupplierQuote(CompanyScopedModel):
    """Ценовое предложение поставщика по позиции RFQ."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    rfq_supplier = models.ForeignKey(
        RFQSupplier, on_delete=models.CASCADE,
        related_name="quotes", verbose_name=_("RFQ supplier"),
    )
    material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Material ID"),
    )
    unit_price = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Unit price"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    delivery_days = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Delivery days"),
    )

    class Meta:
        db_table = 'procurement"."procurement_supplier_quote'
        verbose_name = _("Supplier quote")
        verbose_name_plural = _("Supplier quotes")
        ordering = ["rfq_supplier", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_supplier_quote_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.unit_price} × {self.quantity}"


# ============================================================
# ЗАКАЗЫ ПОСТАВЩИКАМ (PO)
# ============================================================

class Order(CompanyScopedModel):
    """Заказ поставщику (Purchase Order)."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("sent", _("Sent")),
        ("confirmed", _("Confirmed")),
        ("partially_received", _("Partially received")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    order_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Order number"),
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT,
        related_name="orders", verbose_name=_("Supplier"),
    )
    requisition = models.ForeignKey(
        Requisition, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="orders", verbose_name=_("Requisition"),
    )
    rfq = models.ForeignKey(
        RFQ, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="orders", verbose_name=_("RFQ"),
    )
    order_date = models.DateField(db_index=True, verbose_name=_("Order date"))
    expected_delivery_date = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Expected delivery date"),
    )
    actual_delivery_date = models.DateField(
        null=True, blank=True, verbose_name=_("Actual delivery date"),
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
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'procurement"."procurement_order'
        verbose_name = _("Purchase order")
        verbose_name_plural = _("Purchase orders")
        ordering = ["-order_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_order_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "order_number"],
                name="uq_proc_order_company_number",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "supplier"]),
        ]

    def __str__(self):
        return f"{self.order_number} ({self.get_status_display()})"


class OrderLine(CompanyScopedModel):
    """Позиция заказа поставщику."""
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
    total_price = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Total price"),
    )
    received_quantity = models.DecimalField(
        max_digits=15, decimal_places=6, default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Received quantity"),
    )

    class Meta:
        db_table = 'procurement"."procurement_order_line'
        verbose_name = _("Order line")
        verbose_name_plural = _("Order lines")
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_order_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity} × {self.unit_price}"


class OrderHistory(CompanyScopedModel):
    """История изменений статуса заказа (аудит)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="history", verbose_name=_("Order"),
    )
    changed_at = models.DateTimeField(db_index=True, verbose_name=_("Changed at"))
    changed_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Changed by employee ID"),
    )
    status_from = models.CharField(
        max_length=20, blank=True, verbose_name=_("From"),
    )
    status_to = models.CharField(max_length=20, blank=True, verbose_name=_("To"))
    comment = models.TextField(blank=True, verbose_name=_("Comment"))

    class Meta:
        db_table = 'procurement"."procurement_order_history'
        verbose_name = _("Order history")
        verbose_name_plural = _("Order history")
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.order.order_number}: {self.status_from} → {self.status_to}"


class Delivery(CompanyScopedModel):
    """Фактическая поставка по заказу (может быть частичной)."""
    STATUS_CHOICES = [
        ("planned", _("Planned")),
        ("in_transit", _("In transit")),
        ("received", _("Received")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE,
        related_name="deliveries", verbose_name=_("Order"),
    )
    delivery_date = models.DateField(db_index=True, verbose_name=_("Delivery date"))
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="received",
        db_index=True, verbose_name=_("Status"),
    )

    class Meta:
        db_table = 'procurement"."procurement_delivery'
        verbose_name = _("Delivery")
        verbose_name_plural = _("Deliveries")
        ordering = ["-delivery_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_proc_delivery_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity} ({self.get_status_display()})"