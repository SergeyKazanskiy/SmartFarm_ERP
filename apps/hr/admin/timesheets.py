"""Админка табелирования."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.hr.models import HRTimesheet


@admin.register(HRTimesheet)
class HRTimesheetAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "work_date", "hours_worked",
        "overtime_hours", "status", "company",
    )
    list_filter = ("company", "status")
    autocomplete_fields = ("employee", "company")
    date_hierarchy = "work_date"
    list_select_related = ("employee",)
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description=_("Утвердить выбранные табели"))
    def approve_selected(self, request, queryset):
        queryset.filter(status="submitted").update(
            status="approved", approved_at=timezone.now(),
        )

    @admin.action(description=_("Отклонить выбранные табели"))
    def reject_selected(self, request, queryset):
        queryset.filter(status="submitted").update(status="rejected")