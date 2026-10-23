"""Админка документов: приход, перемещение, списание, резервирование."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.wms.models import (
    GoodsReceipt, GoodsReceiptLine, MaterialReservation,
    Transfer, TransferLine, WriteOff, WriteOffLine,
)


class GoodsReceiptLineInline(admin.TabularInline):
    model = GoodsReceiptLine
    extra = 0
    fields = ("code", "material", "lot", "location", "quantity", "unit_cost")
    autocomplete_fields = ("material", "lot", "location")


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "warehouse", "counterparty_id",
        "receipt_date", "status", "company",
    )
    list_filter = ("company", "status", "warehouse")
    search_fields = ("code",)
    autocomplete_fields = ("warehouse", "company")
    readonly_fields = ("created_at", "updated_at", "posted_at")
    date_hierarchy = "receipt_date"
    list_select_related = ("warehouse",)
    inlines = [GoodsReceiptLineInline]


@admin.register(GoodsReceiptLine)
class GoodsReceiptLineAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "receipt", "material", "lot",
        "location", "quantity", "unit_cost", "company",
    )
    list_filter = ("company",)
    autocomplete_fields = ("receipt", "material", "lot", "location", "company")


class TransferLineInline(admin.TabularInline):
    model = TransferLine
    extra = 0
    fields = ("code", "material", "quantity")
    autocomplete_fields = ("material",)


@admin.register(Transfer)
class TransferAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "from_warehouse", "to_warehouse",
        "transfer_date", "status", "company",
    )
    list_filter = ("company", "status", "from_warehouse", "to_warehouse")
    search_fields = ("code",)
    autocomplete_fields = ("from_warehouse", "to_warehouse", "company")
    readonly_fields = ("created_at", "updated_at", "posted_at")
    date_hierarchy = "transfer_date"
    inlines = [TransferLineInline]


@admin.register(TransferLine)
class TransferLineAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "transfer", "material", "quantity", "company")
    list_filter = ("company",)
    autocomplete_fields = ("transfer", "material", "company")


class WriteOffLineInline(admin.TabularInline):
    model = WriteOffLine
    extra = 0
    fields = ("code", "material", "quantity")
    autocomplete_fields = ("material",)


@admin.register(WriteOff)
class WriteOffAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "warehouse", "writeoff_date",
        "status", "company",
    )
    list_filter = ("company", "status", "warehouse")
    search_fields = ("code", "reason")
    autocomplete_fields = ("warehouse", "company")
    readonly_fields = ("created_at", "updated_at", "posted_at")
    date_hierarchy = "writeoff_date"
    inlines = [WriteOffLineInline]


@admin.register(WriteOffLine)
class WriteOffLineAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "writeoff", "material", "quantity", "company")
    list_filter = ("company",)
    autocomplete_fields = ("writeoff", "material", "company")


@admin.register(MaterialReservation)
class MaterialReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "material", "warehouse", "quantity", "status",
        "task_object_type", "task_object_id",
        "reserved_at", "issued_at", "released_at", "company",
    )
    list_filter = ("company", "status", "warehouse")
    search_fields = ("code", "task_object_type")
    autocomplete_fields = ("material", "warehouse", "company")
    readonly_fields = ("created_at", "updated_at", "reserved_at", "issued_at", "released_at")
    date_hierarchy = "reserved_at"
    list_select_related = ("material", "warehouse")