"""Админка номенклатуры."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.wms.models import (
    Material, MaterialGroup, MaterialLot, SerialNumber,
)


@admin.register(MaterialGroup)
class MaterialGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "parent", "company")
    list_filter = ("company", "parent")
    search_fields = ("code", "name")
    autocomplete_fields = ("parent", "company")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "material_code", "name",
        "material_group", "barcode", "min_stock_level", "company",
    )
    list_filter = ("company", "material_group")
    search_fields = ("code", "material_code", "name", "barcode")
    autocomplete_fields = ("material_group", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("material_group",)

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "material_code", "name"),
        }),
        (_("Классификация и учёт"), {
            "fields": ("material_group", "unit_id", "barcode"),
        }),
        (_("Запас"), {
            "fields": ("min_stock_level",),
        }),
        (_("Служебное"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(MaterialLot)
class MaterialLotAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "material", "lot_number",
        "manufacture_date", "expiration_date", "company",
    )
    list_filter = ("company", "material")
    search_fields = ("code", "lot_number")
    autocomplete_fields = ("material", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "expiration_date"


@admin.register(SerialNumber)
class SerialNumberAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "material", "serial_number", "company")
    list_filter = ("company", "material")
    search_fields = ("code", "serial_number")
    autocomplete_fields = ("material", "company")