"""Админка инвентаризации."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.wms.models import InventorySnapshot, InventorySnapshotItem


class InventorySnapshotItemInline(admin.TabularInline):
    model = InventorySnapshotItem
    extra = 0
    fields = ("code", "inventory", "quantity", "counted_quantity")
    autocomplete_fields = ("inventory",)


@admin.register(InventorySnapshot)
class InventorySnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "warehouse", "snapshot_date", "status", "company",
    )
    list_filter = ("company", "status", "warehouse")
    search_fields = ("code",)
    autocomplete_fields = ("warehouse", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "snapshot_date"
    list_select_related = ("warehouse",)
    inlines = [InventorySnapshotItemInline]


@admin.register(InventorySnapshotItem)
class InventorySnapshotItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "snapshot", "inventory",
        "quantity", "counted_quantity", "company",
    )
    list_filter = ("company", "snapshot")
    autocomplete_fields = ("snapshot", "inventory", "company")