"""
Модели WMS-модуля. Таблицы — в схеме `wms`.

Ключевые концепции:
- `wms_inventory` — текущие остатки по (material, location, lot, serial).
- `wms_inventory_transaction` — журнал движений (итоговая проекция).
- `goods_receipt` / `transfer` / `writeoff` — документы с `draft → posted`.
- `material_reservation` — резервирование (reserved → issued/released).
- `inventory_snapshot` — инвентаризация (draft → counted → approved).

Соглашения (как в предыдущих модулях):
- PK = BigAutoField (`id`).
- `code` = человекочитаемый ID (WH-001, MAT-001, LOC-W-001).
- Внешние ссылки (address_id, counterparty_id, document_id, unit_id, task_object_id) — BigIntegerField.
- Внутренние FK — ForeignKey с CASCADE/PROTECT/SET_NULL.
- `created_at`/`updated_at` — из CompanyScopedModel.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import CompanyScopedModel


# ============================================================
# СКЛАДЫ И ЯЧЕЙКИ
# ============================================================

class WarehouseType(CompanyScopedModel):
    """Тип склада: центральный, приобъектный, готовой продукции."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))

    class Meta:
        db_table = 'wms"."wms_warehouse_type'
        verbose_name = _("Warehouse type")
        verbose_name_plural = _("Warehouse types")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_warehouse_type_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class Warehouse(CompanyScopedModel):
    """Склад."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))
    warehouse_type = models.ForeignKey(
        WarehouseType, on_delete=models.PROTECT, null=True, blank=True,
        related_name="warehouses", verbose_name=_("Warehouse type"),
    )
    # Ссылка на dict_address (внешний модуль)
    address_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Address ID"),
    )

    class Meta:
        db_table = 'wms"."wms_warehouse'
        verbose_name = _("Warehouse")
        verbose_name_plural = _("Warehouses")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_warehouse_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class StorageLocation(CompanyScopedModel):
    """Ячейка хранения."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE,
        related_name="locations", verbose_name=_("Warehouse"),
    )
    location_code = models.CharField(
        max_length=50, db_index=True, verbose_name=_("Location code"),
    )
    location_type = models.CharField(
        max_length=50, blank=True, verbose_name=_("Location type"),
        help_text="паллетное / стеллажное / …",
    )

    class Meta:
        db_table = 'wms"."wms_storage_location'
        verbose_name = _("Storage location")
        verbose_name_plural = _("Storage locations")
        ordering = ["warehouse", "location_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_storage_location_company_code",
            ),
            models.UniqueConstraint(
                fields=["warehouse", "location_code"],
                name="uq_wms_storage_location_warehouse_code",
            ),
        ]

    def __str__(self):
        return f"{self.warehouse.name} / {self.location_code}"


# ============================================================
# НОМЕНКЛАТУРА
# ============================================================

class MaterialGroup(CompanyScopedModel):
    """Группа материалов (иерархическая)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, db_index=True, verbose_name=_("Name"))
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children", verbose_name=_("Parent group"),
    )

    class Meta:
        db_table = 'wms"."wms_material_group'
        verbose_name = _("Material group")
        verbose_name_plural = _("Material groups")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_material_group_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class Material(CompanyScopedModel):
    """
    Номенклатурная позиция. Общая для Construction, ТОиР, Production (BOM).
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    material_group = models.ForeignKey(
        MaterialGroup, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="materials", verbose_name=_("Material group"),
    )
    material_code = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Material code"),
    )
    name = models.CharField(
        max_length=500, db_index=True, verbose_name=_("Name"),
    )
    # Ссылка на dict_unit (внешний модуль)
    unit_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Unit ID"),
    )
    barcode = models.CharField(
        max_length=100, blank=True, db_index=True, verbose_name=_("Barcode"),
    )
    min_stock_level = models.DecimalField(
        max_digits=15, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Min stock level"),
        help_text="Точка перезаказа",
    )

    class Meta:
        db_table = 'wms"."wms_material'
        verbose_name = _("Material")
        verbose_name_plural = _("Materials")
        ordering = ["material_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_material_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "material_code"],
                name="uq_wms_material_company_material_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "material_group"]),
        ]

    def __str__(self):
        return f"{self.material_code} {self.name}"


class MaterialLot(CompanyScopedModel):
    """Партия материала (сроки годности, сертификаты)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    material = models.ForeignKey(
        Material, on_delete=models.CASCADE,
        related_name="lots", verbose_name=_("Material"),
    )
    lot_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Lot number"),
    )
    manufacture_date = models.DateField(
        null=True, blank=True, verbose_name=_("Manufacture date"),
    )
    expiration_date = models.DateField(
        null=True, blank=True, db_index=True, verbose_name=_("Expiration date"),
    )

    class Meta:
        db_table = 'wms"."wms_material_lot'
        verbose_name = _("Material lot")
        verbose_name_plural = _("Material lots")
        ordering = ["-expiration_date", "lot_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_material_lot_company_code",
            ),
            models.UniqueConstraint(
                fields=["material", "lot_number"],
                name="uq_wms_material_lot_material_number",
            ),
        ]

    def __str__(self):
        return self.lot_number


class SerialNumber(CompanyScopedModel):
    """Серийный номер (поштучный учёт)."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    material = models.ForeignKey(
        Material, on_delete=models.CASCADE,
        related_name="serial_numbers", verbose_name=_("Material"),
    )
    serial_number = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Serial number"),
    )

    class Meta:
        db_table = 'wms"."wms_serial_number'
        verbose_name = _("Serial number")
        verbose_name_plural = _("Serial numbers")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_serial_number_company_code",
            ),
            models.UniqueConstraint(
                fields=["material", "serial_number"],
                name="uq_wms_serial_number_material_number",
            ),
        ]

    def __str__(self):
        return self.serial_number


# ============================================================
# ОСТАТКИ
# ============================================================

class Inventory(CompanyScopedModel):
    """
    Остаток материала в конкретной ячейке.
    Уникальный ключ: (company, material, location, lot, serial).
    `unit_cost` — скользящее среднее.
    """
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name="inventory", verbose_name=_("Material"),
    )
    location = models.ForeignKey(
        StorageLocation, on_delete=models.PROTECT,
        related_name="inventory", verbose_name=_("Location"),
    )
    lot = models.ForeignKey(
        MaterialLot, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory", verbose_name=_("Lot"),
    )
    serial = models.ForeignKey(
        SerialNumber, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="inventory", verbose_name=_("Serial number"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6, default=0,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    unit_cost = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Unit cost"),
        help_text="Скользящее среднее",
    )

    class Meta:
        db_table = 'wms"."wms_inventory'
        verbose_name = _("Inventory")
        verbose_name_plural = _("Inventory")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_inventory_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "material", "location"]),
        ]

    def __str__(self):
        return f"{self.material.material_code} @ {self.location.location_code}: {self.quantity}"


# ============================================================
# РЕЗЕРВИРОВАНИЕ
# ============================================================

class MaterialReservation(CompanyScopedModel):
    """
    Резервирование материала под задачу любого модуля.
    Жизненный цикл: reserved → issued (выдано) | released (снято).
    """
    STATUS_CHOICES = [
        ("reserved", _("Reserved")),
        ("issued", _("Issued")),
        ("released", _("Released")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name="reservations", verbose_name=_("Material"),
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, null=True, blank=True,
        related_name="reservations", verbose_name=_("Warehouse"),
    )
    # Ссылка на объект любого модуля (task, project, production_order, …)
    task_object_type = models.CharField(
        max_length=50, blank=True, db_index=True,
        verbose_name=_("Task object type"),
    )
    task_object_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Task object ID"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="reserved",
        db_index=True, verbose_name=_("Status"),
    )
    reserved_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Reserved at"),
    )
    issued_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Issued at"),
    )
    released_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Released at"),
    )

    class Meta:
        db_table = 'wms"."wms_material_reservation'
        verbose_name = _("Material reservation")
        verbose_name_plural = _("Material reservations")
        ordering = ["-reserved_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_material_reservation_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "material", "status"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.material.material_code} × {self.quantity} [{self.status}]"


# ============================================================
# ЖУРНАЛ ДВИЖЕНИЙ
# ============================================================

class InventoryTransaction(CompanyScopedModel):
    """
    Журнал всех складских движений.
    source_document_type/source_document_id связывают движение с документом-основанием
    (goods_receipt / transfer / writeoff / inventory_snapshot / material_reservation).
    """
    TYPE_CHOICES = [
        ("receipt", _("Receipt")),
        ("issue", _("Issue")),
        ("transfer_out", _("Transfer out")),
        ("transfer_in", _("Transfer in")),
        ("writeoff", _("Write-off")),
        ("reservation_issue", _("Reservation issue")),
    ]
    SOURCE_TYPE_CHOICES = [
        ("wms_goods_receipt", _("Goods receipt")),
        ("wms_transfer", _("Transfer")),
        ("wms_writeoff", _("Write-off")),
        ("wms_inventory_snapshot", _("Inventory snapshot")),
        ("wms_material_reservation", _("Material reservation")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    inventory = models.ForeignKey(
        Inventory, on_delete=models.PROTECT,
        related_name="transactions", verbose_name=_("Inventory"),
    )
    transaction_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES,
        db_index=True, verbose_name=_("Transaction type"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        verbose_name=_("Quantity"),
        help_text="Знак зависит от типа (для receipt/transfer_in — плюс, для issue/writeoff — минус)",
    )
    source_document_type = models.CharField(
        max_length=50, choices=SOURCE_TYPE_CHOICES, blank=True,
        db_index=True, verbose_name=_("Source document type"),
    )
    source_document_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Source document ID"),
    )
    reservation = models.ForeignKey(
        MaterialReservation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="transactions", verbose_name=_("Reservation"),
    )
    task_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Task ID"),
    )
    transaction_date = models.DateTimeField(
        db_index=True, verbose_name=_("Transaction date"),
    )

    class Meta:
        db_table = 'wms"."wms_inventory_transaction'
        verbose_name = _("Inventory transaction")
        verbose_name_plural = _("Inventory transactions")
        ordering = ["-transaction_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_inventory_transaction_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "inventory"]),
            models.Index(fields=["company", "transaction_type"]),
        ]

    def __str__(self):
        return f"{self.code}: {self.transaction_type} {self.quantity}"


# ============================================================
# ДОКУМЕНТЫ: ПРИХОД / ПЕРЕМЕЩЕНИЕ / СПИСАНИЕ
# ============================================================

class GoodsReceipt(CompanyScopedModel):
    """Приходный документ."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("posted", _("Posted")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT,
        related_name="receipts", verbose_name=_("Warehouse"),
    )
    # Ссылка на CP.counterparty (внешний модуль)
    counterparty_id = models.BigIntegerField(
        null=True, blank=True, db_index=True,
        verbose_name=_("Counterparty ID"),
    )
    receipt_date = models.DateTimeField(db_index=True, verbose_name=_("Receipt date"))
    # Ссылка на DOC.document (внешний модуль)
    document_id = models.BigIntegerField(
        null=True, blank=True, verbose_name=_("Document ID"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    posted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Posted at"),
    )

    class Meta:
        db_table = 'wms"."wms_goods_receipt'
        verbose_name = _("Goods receipt")
        verbose_name_plural = _("Goods receipts")
        ordering = ["-receipt_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_goods_receipt_company_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"


class GoodsReceiptLine(CompanyScopedModel):
    """Позиция приходного документа."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    receipt = models.ForeignKey(
        GoodsReceipt, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Receipt"),
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name="receipt_lines", verbose_name=_("Material"),
    )
    lot = models.ForeignKey(
        MaterialLot, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="receipt_lines", verbose_name=_("Lot"),
    )
    location = models.ForeignKey(
        StorageLocation, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="receipt_lines", verbose_name=_("Location"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )
    unit_cost = models.DecimalField(
        max_digits=15, decimal_places=4, null=True, blank=True,
        validators=[MinValueValidator(0)], verbose_name=_("Unit cost"),
    )

    class Meta:
        db_table = 'wms"."wms_goods_receipt_line'
        verbose_name = _("Goods receipt line")
        verbose_name_plural = _("Goods receipt lines")
        ordering = ["receipt", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_goods_receipt_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.material.material_code} × {self.quantity}"


class Transfer(CompanyScopedModel):
    """Документ перемещения между складами."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("posted", _("Posted")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    from_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT,
        related_name="transfers_out", verbose_name=_("From warehouse"),
    )
    to_warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT,
        related_name="transfers_in", verbose_name=_("To warehouse"),
    )
    transfer_date = models.DateTimeField(db_index=True, verbose_name=_("Transfer date"))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    posted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Posted at"),
    )

    class Meta:
        db_table = 'wms"."wms_transfer'
        verbose_name = _("Transfer")
        verbose_name_plural = _("Transfers")
        ordering = ["-transfer_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_transfer_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"


class TransferLine(CompanyScopedModel):
    """Позиция перемещения."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    transfer = models.ForeignKey(
        Transfer, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Transfer"),
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name="transfer_lines", verbose_name=_("Material"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )

    class Meta:
        db_table = 'wms"."wms_transfer_line'
        verbose_name = _("Transfer line")
        verbose_name_plural = _("Transfer lines")
        ordering = ["transfer", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_transfer_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.material.material_code} × {self.quantity}"


class WriteOff(CompanyScopedModel):
    """Документ списания материалов."""
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("posted", _("Posted")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT,
        related_name="writeoffs", verbose_name=_("Warehouse"),
    )
    writeoff_date = models.DateTimeField(db_index=True, verbose_name=_("Write-off date"))
    reason = models.TextField(blank=True, verbose_name=_("Reason"))
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )
    posted_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Posted at"),
    )

    class Meta:
        db_table = 'wms"."wms_writeoff'
        verbose_name = _("Write-off")
        verbose_name_plural = _("Write-offs")
        ordering = ["-writeoff_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_writeoff_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"


class WriteOffLine(CompanyScopedModel):
    """Позиция списания."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    writeoff = models.ForeignKey(
        WriteOff, on_delete=models.CASCADE,
        related_name="lines", verbose_name=_("Write-off"),
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name="writeoff_lines", verbose_name=_("Material"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("Quantity"),
    )

    class Meta:
        db_table = 'wms"."wms_writeoff_line'
        verbose_name = _("Write-off line")
        verbose_name_plural = _("Write-off lines")
        ordering = ["writeoff", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_writeoff_line_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.material.material_code} × {self.quantity}"


# ============================================================
# ТАРА
# ============================================================

class ContainerType(CompanyScopedModel):
    """Тип тары/контейнера."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    name = models.CharField(max_length=255, verbose_name=_("Name"))

    class Meta:
        db_table = 'wms"."wms_container_type'
        verbose_name = _("Container type")
        verbose_name_plural = _("Container types")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_container_type_company_code",
            ),
        ]

    def __str__(self):
        return self.name


class Container(CompanyScopedModel):
    """Тара/контейнер."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    container_type = models.ForeignKey(
        ContainerType, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="containers", verbose_name=_("Container type"),
    )
    container_code = models.CharField(
        max_length=100, db_index=True, verbose_name=_("Container code"),
    )

    class Meta:
        db_table = 'wms"."wms_container'
        verbose_name = _("Container")
        verbose_name_plural = _("Containers")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_container_company_code",
            ),
            models.UniqueConstraint(
                fields=["company", "container_code"],
                name="uq_wms_container_company_container_code",
            ),
        ]

    def __str__(self):
        return self.container_code


class ContainerItem(CompanyScopedModel):
    """Содержимое тары."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE,
        related_name="items", verbose_name=_("Container"),
    )
    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE,
        related_name="container_items", verbose_name=_("Inventory"),
    )

    class Meta:
        db_table = 'wms"."wms_container_item'
        verbose_name = _("Container item")
        verbose_name_plural = _("Container items")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_container_item_company_code",
            ),
            models.UniqueConstraint(
                fields=["container", "inventory"],
                name="uq_wms_container_item_pair",
            ),
        ]

    def __str__(self):
        return f"{self.container.container_code} ← {self.inventory.material.material_code}"


# ============================================================
# ИНВЕНТАРИЗАЦИЯ
# ============================================================

class InventorySnapshot(CompanyScopedModel):
    """
    Инвентаризация: снимок системных остатков + пересчёт + утверждение.
    Жизненный цикл: draft → counted → approved.
    """
    STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("counted", _("Counted")),
        ("approved", _("Approved")),
    ]

    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT,
        related_name="inventory_snapshots", verbose_name=_("Warehouse"),
    )
    snapshot_date = models.DateTimeField(
        db_index=True, verbose_name=_("Snapshot date"),
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="draft",
        db_index=True, verbose_name=_("Status"),
    )

    class Meta:
        db_table = 'wms"."wms_inventory_snapshot'
        verbose_name = _("Inventory snapshot")
        verbose_name_plural = _("Inventory snapshots")
        ordering = ["-snapshot_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_inventory_snapshot_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_status_display()})"


class InventorySnapshotItem(CompanyScopedModel):
    """Позиция инвентаризации: системное и фактическое количество."""
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(max_length=50, db_index=True, verbose_name=_("Code"))
    snapshot = models.ForeignKey(
        InventorySnapshot, on_delete=models.CASCADE,
        related_name="items", verbose_name=_("Snapshot"),
    )
    inventory = models.ForeignKey(
        Inventory, on_delete=models.CASCADE,
        related_name="snapshot_items", verbose_name=_("Inventory"),
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=6,
        validators=[MinValueValidator(0)], verbose_name=_("System quantity"),
    )
    counted_quantity = models.DecimalField(
        max_digits=15, decimal_places=6, null=True, blank=True,
        validators=[MinValueValidator(0)],
        verbose_name=_("Counted quantity"),
    )

    class Meta:
        db_table = 'wms"."wms_inventory_snapshot_item'
        verbose_name = _("Inventory snapshot item")
        verbose_name_plural = _("Inventory snapshot items")
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                name="uq_wms_inventory_snapshot_item_company_code",
            ),
        ]

    def __str__(self):
        return f"{self.inventory.material.material_code}: {self.quantity} → {self.counted_quantity or '—'}"