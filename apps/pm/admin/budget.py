"""Админка бюджета."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.pm.models import Budget, BudgetItem


class BudgetItemInline(admin.TabularInline):
    model = BudgetItem
    extra = 0
    fields = ("code", "category", "planned_amount", "actual_amount", "description")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "project", "name", "total_planned_amount",
        "total_actual_amount", "status", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "name", "project__name")
    autocomplete_fields = ("project", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("project",)
    inlines = [BudgetItemInline]

    actions = ["approve_selected"]

    @admin.action(description=_("Утвердить бюджеты"))
    def approve_selected(self, request, queryset):
        queryset.filter(status="draft").update(
            status="approved", approved_at=timezone.now(),
        )


@admin.register(BudgetItem)
class BudgetItemAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "budget", "category",
        "planned_amount", "actual_amount", "company",
    )
    list_filter = ("company", "category")
    search_fields = ("code", "description")
    autocomplete_fields = ("budget", "company")