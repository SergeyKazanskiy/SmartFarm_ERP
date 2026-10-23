"""Админка остатков и журнала движений."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.wms.models import Inventory, InventoryTransaction


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "material", "location", "lot",
        "quantity", "unit_cost", "company",
    )
    list_filter = ("company", "material", "location")
    search_fields = ("code", "material__material_code", "location__location_code")
    autocomplete_fields = ("material", "location", "lot", "serial", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("material", "location")

    actions = ["zero_out"]

    @admin.action(description=_("Обнулить остатки (только для тестов)"))
    def zero_out(self, request, queryset):
        queryset.update(quantity=0)


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "inventory", "transaction_type",
        "quantity", "source_document_type", "source_document_id",
        "transaction_date", "company",
    )
    list_filter = ("company", "transaction_type", "source_document_type")
    search_fields = ("code",)
    autocomplete_fields = ("inventory", "reservation", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "transaction_date"
    list_select_related = ("inventory",)