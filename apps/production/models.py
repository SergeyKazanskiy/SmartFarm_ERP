"""
Модели Production-модуля. Таблицы — в схеме `production`.

Ключевые концепции:
- Technology → Routing → OperationDefinition → QualityPoint (мастер-данные).
- Bom → BomItem (спецификация изделия).
- ProductionOrder → WorkOrder → OperationExecution (исполнительный цикл).

JSON-поля:
- resources_json / parameters_json — в OperationDefinition.
- actual_materials_json — в WorkOrder.
- measurements_json / quality_results_json — в OperationExecution.

Соглашения (как в предыдущих модулях):
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (TECH-001, ROUT-001, OP-DEF-001, PROD-001…).
- Внешние ссылки (product_material_id, material_id, performed_by_employee_id,
  created_by_employee_id) — BigIntegerField.
- Внутренние FK — ForeignKey с CASCADE/PROTECT/SET_NULL.
- `created_at`/`updated_at` — из CompanyScopedModel.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# МАСТЕР-ДАННЫЕ: ТЕХНОЛОГИЯ, МАРШРУТ, ЦЕНТРЫ
# ============================================================

class Technology(CompanyScopedModel):
    """Справочник технологий производства."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'production"."prod_technology'
        verbose_name = _("Technology")
        verbose_name_plural = _("Technologies")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_technology_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class WorkCenter(CompanyScopedModel):
    """Рабочий центр (участок / линия)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'production"."prod_work_center'
        verbose_name = _("Work center")
        verbose_name_plural = _("Work centers")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_work_center_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class Routing(CompanyScopedModel):
    """Технологический маршрут."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    technology = models.ForeignKey(
        Technology, on_delete=models.PROTECT, null=True, blank=True,
        related_name="routings", verbose_name=_("Technology"),
    )
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'production"."prod_routing'
        verbose_name = _("Routing")
        verbose_name_plural = _("Routings")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_routing_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class OperationDefinition(CompanyScopedModel):
    """
    Операция маршрута.
    resources_json: [{"resource_type": "employee", "quantity": 2}]
    parameters_json: [{"name": "temperature", "target_value": 180, "tolerance": 5}]
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    routing = models.ForeignKey(
        Routing, on_delete=models.CASCADE,
        related_name="operations", verbose_name=_("Routing"),
    )
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Operation name"))
    sequence_no = models.PositiveIntegerField(
        default=1, verbose_name=_("Sequence number"),
    )
    work_center = models.ForeignKey(
        WorkCenter, on_delete=models.PROTECT, null=True, blank=True,
        related_name="operations", verbose_name=_("Work center"),
    )
    resources_json = models.JSONField(
        default=list, blank=True, verbose_name=_("Resources"),
    )
    parameters_json = models.JSONField(
        default=list, blank=True, verbose_name=_("Parameters"),
    )

    class Meta:
        db_table = 'production"."prod_operation_definition'
        verbose_name = _("Operation definition")
        verbose_name_plural = _("Operation definitions")
        ordering = ["routing", "sequence_no"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_operation_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name} (#{self.sequence_no})"


class QualityPoint(CompanyScopedModel):
    """Контрольная точка качества на операции."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    operation = models.ForeignKey(
        OperationDefinition, on_delete=models.CASCADE,
        related_name="quality_points", verbose_name=_("Operation"),
    )
    name = models.CharField(max_length=255, verbose_name=_("Quality point name"))

    class Meta:
        db_table = 'production"."prod_quality_point'
        verbose_name = _("Quality point")
        verbose_name_plural = _("Quality points")
        ordering = ["operation", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_quality_point_company_code",
            ),
        ]

    def __str__(self):
        return self.name


# ============================================================
# СПЕЦИФИКАЦИЯ (BOM)
# ============================================================

class Bom(CompanyScopedModel):
    """Спецификация изделия."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    product_material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Product material ID"),
        help_text="Готовое изделие (ссылка на wms_material)",
    )
    name = models.CharField(max_length=500, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'production"."prod_bom'
        verbose_name = _("BOM")
        verbose_name_plural = _("BOMs")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_bom_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class BomItem(CompanyScopedModel):
    """Позиция спецификации."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    bom = models.ForeignKey(
        Bom, on_delete=models.CASCADE,
        related_name="items", verbose_name=_("BOM"),
    )
    material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Material ID"),
        help_text="Компонент (ссылка на wms_material)",
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    unit_cost = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Unit cost"),
        help_text="Плановая цена за единицу компонента",
    )

    class Meta:
        db_table = 'production"."prod_bom_item'
        verbose_name = _("BOM item")
        verbose_name_plural = _("BOM items")
        ordering = ["bom", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_bom_item_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code}: {self.quantity} × mat#{self.material_id}"


class MaterialPriceHistory(CompanyScopedModel):
    """История плановых цен компонентов для расчёта себестоимости BOM."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    material_id = models.BigIntegerField(
        db_index=True, verbose_name=_("Material ID"),
    )
    unit_cost = models.DecimalField(
        max_digits=15, decimal_places=4,
        validators=[MinValueValidator(0)], verbose_name=_("Unit cost"),
    )
    effective_date = models.DateField(db_index=True, verbose_name=_("Effective date"))
    created_by_employee_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Created by employee ID"),
    )

    class Meta:
        db_table = 'production"."prod_material_price_history'
        verbose_name = _("Material price history")
        verbose_name_plural = _("Material price history")
        ordering = ["-effective_date"]
        indexes = [
            models.Index(fields=["company", "material_id", "effective_date"]),
        ]

    def __str__(self):
        return f"mat#{self.material_id} @ {self.effective_date}: {self.unit_cost}"


# ============================================================
# ЗАКАЗ НА ПРОИЗВОДСТВО
# ============================================================

class ProductionOrder(CompanyScopedModel):
    """Заказ на производство."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("confirmed", _("Confirmed")),
        ("in_progress", _("In progress")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    bom = models.ForeignKey(
        Bom, on_delete=models.PROTECT, null=True, blank=True,
        related_name="production_orders", verbose_name=_("BOM"),
    )
    routing = models.ForeignKey(
        Routing, on_delete=models.PROTECT, null=True, blank=True,
        related_name="production_orders", verbose_name=_("Routing"),
    )
    planned_quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Planned quantity"),
    )
    planned_start_date = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Planned start date"),
    )
    planned_end_date = models.DateField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Planned end date"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )

    class Meta:
        db_table = 'production"."prod_production_order'
        verbose_name = _("Production order")
        verbose_name_plural = _("Production orders")
        ordering = ["-planned_start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_production_order_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"


# ============================================================
# НАРЯД (WORK ORDER)
# ============================================================

class WorkOrder(CompanyScopedModel):
    """Исполнительный наряд по производственному заказу."""
    STATUS_CHOICES = [
        ("planned", _("Planned")),
        ("in_progress", _("In progress")),
        ("on_hold", _("On hold")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    production_order = models.ForeignKey(
        ProductionOrder, on_delete=models.CASCADE,
        related_name="work_orders", verbose_name=_("Production order"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="planned",
        db_index=True, verbose_name=_("Status"),
    )
    planned_start = models.DateTimeField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Planned start"),
    )
    planned_finish = models.DateTimeField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Planned finish"),
    )
    actual_start = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Actual start"),
    )
    actual_finish = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Actual finish"),
    )
    actual_materials_json = models.JSONField(
        default=list, blank=True, verbose_name=_("Actual materials"),
        help_text="[{'material_id': ..., 'quantity': ..., 'wms_reservation_id': ...}]",
    )

    class Meta:
        db_table = 'production"."prod_work_order'
        verbose_name = _("Work order")
        verbose_name_plural = _("Work orders")
        ordering = ["-planned_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_work_order_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"


# ============================================================
# ВЫПОЛНЕНИЕ ОПЕРАЦИИ
# ============================================================

class OperationExecution(CompanyScopedModel):
    """
    Фактическое выполнение операции.
    measurements_json: [{"parameter_name": "temperature", "measured_value": 21.5, "measured_at": "..."}]
    quality_results_json: [{"quality_point_id": 1, "is_passed": true, "comment": "OK"}]
    """
    STATUS_CHOICES = [
        ("in_progress", _("In progress")),
        ("completed", _("Completed")),
        ("rework", _("Rework")),
        ("cancelled", _("Cancelled")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE,
        related_name="executions", verbose_name=_("Work order"),
    )
    operation = models.ForeignKey(
        OperationDefinition, on_delete=models.PROTECT,
        related_name="executions", verbose_name=_("Operation"),
    )
    work_center = models.ForeignKey(
        WorkCenter, on_delete=models.PROTECT, null=True, blank=True,
        related_name="executions", verbose_name=_("Work center"),
    )
    performed_by_employee_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Performed by employee ID"),
    )
    start_time = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name=_("Start time"),
    )
    end_time = models.DateTimeField(
        null=True, blank=True, verbose_name=_("End time"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="in_progress",
        db_index=True, verbose_name=_("Status"),
    )
    measurements_json = models.JSONField(
        default=list, blank=True, verbose_name=_("Measurements"),
    )
    quality_results_json = models.JSONField(
        default=list, blank=True, verbose_name=_("Quality results"),
    )

    class Meta:
        db_table = 'production"."prod_operation_execution'
        verbose_name = _("Operation execution")
        verbose_name_plural = _("Operation executions")
        ordering = ["-start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_prod_operation_execution_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "work_order"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"