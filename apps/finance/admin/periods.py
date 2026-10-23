"""Админка финансовых периодов и показателей."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.finance.models import FinancialIndicator, FinancialPeriod


@admin.register(FinancialPeriod)
class FinancialPeriodAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "date_from", "date_to", "is_closed", "company")
    list_filter = ("company", "is_closed")
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date_from"

    actions = ["close_periods"]

    @admin.action(description=_("Закрыть периоды"))
    def close_periods(self, request, queryset):
        queryset.filter(is_closed=False).update(is_closed=True)


@admin.register(FinancialIndicator)
class FinancialIndicatorAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "indicator_code", "financial_project",
        "period", "indicator_value", "company",
    )
    list_filter = ("company", "indicator_code")
    search_fields = ("code", "indicator_code")
    autocomplete_fields = ("financial_project", "period", "company")