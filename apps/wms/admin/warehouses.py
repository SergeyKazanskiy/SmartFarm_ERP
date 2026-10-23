"""Админка складов и ячеек."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.wms.models import StorageLocation, Warehouse, WarehouseType


@admin.register(WarehouseType)
class WarehouseTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")


class StorageLocationInline(admin.TabularInline):
    model = StorageLocation
    extra = 0
    fields = ("code", "location_code", "location_type")


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "warehouse_type", "address_id", "company")
    list_filter = ("company", "warehouse_type")
    search_fields = ("code", "name")
    autocomplete_fields = ("warehouse_type", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("warehouse_type",)
    inlines = [StorageLocationInline]


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "warehouse", "location_code", "location_type", "company",
    )
    list_filter = ("company", "warehouse")
    search_fields = ("code", "location_code")
    autocomplete_fields = ("warehouse", "company")
    readonly_fields = ("created_at", "updated_at")