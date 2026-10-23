"""Админка сделок."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.crm.models import Opportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "title", "opportunity_stage",
        "amount", "expected_close_date", "is_won",
        "responsible_employee_id", "company",
    )
    list_filter = ("company", "opportunity_stage", "is_won")
    search_fields = ("code", "title", "lost_reason")
    autocomplete_fields = ("lead", "opportunity_stage", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "expected_close_date"
    list_select_related = ("opportunity_stage", "lead")

    actions = ["mark_won", "mark_lost"]

    @admin.action(description=_("Сделка выиграна"))
    def mark_won(self, request, queryset):
        queryset.filter(is_won__isnull=True).update(is_won=1)

    @admin.action(description=_("Сделка проиграна"))
    def mark_lost(self, request, queryset):
        queryset.filter(is_won__isnull=True).update(is_won=0)