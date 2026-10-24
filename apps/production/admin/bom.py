"""Админка BOM."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.production.models import Bom, BomItem


class BomItemInline(admin.TabularInline):
    model = BomItem
    extra = 0
    fields = ("code", "material_id", "quantity", "unit_cost")


@admin.register(Bom)
class BomAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "product_material_id", "company",
    )
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [BomItemInline]


@admin.register(BomItem)
class BomItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "bom", "material_id",
        "quantity", "unit_cost", "company",
    )
    list_filter = ("company", "bom")
    search_fields = ("code", "material_id")
    autocomplete_fields = ("bom", "company")