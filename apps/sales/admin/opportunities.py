"""Админка воронки продаж."""
from django.contrib import admin

from apps.sales.models import Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "customer", "stage",
        "expected_value", "probability_percent",
        "expected_close_date", "company",
    )
    list_filter = ("company", "stage")
    search_fields = ("code", "name")
    autocomplete_fields = ("customer", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "expected_close_date"
    list_select_related = ("customer",)