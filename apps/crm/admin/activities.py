"""Админка активностей."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.crm.models import Activity


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "activity_type", "activity_date",
        "is_completed", "employee_id", "lead", "opportunity", "company",
    )
    list_filter = ("company", "activity_type", "is_completed")
    search_fields = ("code", "subject", "result")
    autocomplete_fields = ("activity_type", "lead", "opportunity", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "activity_date"
    list_select_related = ("activity_type", "lead", "opportunity")

    actions = ["mark_completed"]

    @admin.action(description=_("Отметить как выполненные"))
    def mark_completed(self, request, queryset):
        queryset.update(is_completed=True, result="выполнено оператором")