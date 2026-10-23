"""Админка бюджетов."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.finance.models import Budget, BudgetItem


class BudgetItemInline(admin.TabularInline):
    model = BudgetItem
    extra = 0
    fields = ("code", "cost_center", "planned_amount")
    autocomplete_fields = ("cost_center",)


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "financial_project", "period_from", "period_to",
        "status", "approved_by_employee_id", "approved_at", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "financial_project__name")
    autocomplete_fields = ("financial_project", "company")
    readonly_fields = ("created_at", "updated_at", "approved_at")
    date_hierarchy = "period_from"
    list_select_related = ("financial_project",)
    inlines = [BudgetItemInline]

    actions = ["approve_budgets"]

    @admin.action(description=_("Утвердить бюджеты"))
    def approve_budgets(self, request, queryset):
        queryset.filter(status="draft").update(
            status="approved", approved_at=timezone.now(),
        )


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "budget", "cost_center", "planned_amount", "company")
    list_filter = ("company", "cost_center")
    search_fields = ("code",)
    autocomplete_fields = ("budget", "cost_center", "company")