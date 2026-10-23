"""Админка прайс-листов."""
from django.contrib import admin

from apps.crm.models import PriceList, PriceListItem


class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 0
    fields = (
        "code", "item_type", "material_id",
        "service_name", "unit_id", "price",
    )


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "valid_from", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)
    date_hierarchy = "valid_from"
    inlines = [PriceListItemInline]


@admin.register(PriceListItem)
class PriceListItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "price_list", "item_type",
        "material_id", "service_name", "price", "company",
    )
    list_filter = ("company", "item_type")
    search_fields = ("code", "service_name")
    autocomplete_fields = ("price_list", "company")