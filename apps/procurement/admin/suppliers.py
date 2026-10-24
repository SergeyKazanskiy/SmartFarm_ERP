"""Админка поставщиков."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.procurement.models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "counterparty_id", "rating",
        "payment_terms", "delivery_terms", "lead_time_days",
        "is_preferred", "company",
    )
    list_filter = ("company", "is_preferred", "payment_terms", "delivery_terms")
    search_fields = ("code",)
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")

    actions = ["mark_preferred", "unmark_preferred"]

    @admin.action(description=_("Отметить как предпочтительных"))
    def mark_preferred(self, request, queryset):
        queryset.update(is_preferred=True)

    @admin.action(description=_("Снять отметку предпочтительных"))
    def unmark_preferred(self, request, queryset):
        queryset.update(is_preferred=False)