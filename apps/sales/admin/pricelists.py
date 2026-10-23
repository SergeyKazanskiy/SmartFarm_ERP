"""Админка прайс-листов."""
from django.contrib import admin

from apps.sales.models import PriceList, PriceListLine


class PriceListLineInline(admin.TabularInline):
    model = PriceListLine
    extra = 0
    fields = ("code", "material_id", "unit_price", "min_quantity")


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "currency_id", "valid_from", "valid_to",
        "is_default", "company",
    )
    list_filter = ("company", "is_default")
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "valid_from"
    inlines = [PriceListLineInline]


@admin.register(PriceListLine)
class PriceListLineAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "price_list", "material_id",
        "unit_price", "min_quantity", "company",
    )
    list_filter = ("company", "price_list")
    search_fields = ("code",)
    autocomplete_fields = ("price_list", "company")