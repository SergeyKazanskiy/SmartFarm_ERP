"""Админка истории статусов и отчётов."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.pm.models import Report, StatusHistory


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "project", "status_from", "status_to",
        "changed_by_employee_id", "changed_at", "company",
    )
    list_filter = ("company", "status_to")
    search_fields = ("project__name", "comment")
    autocomplete_fields = ("project", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "changed_at"


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "project", "report_date",
        "report_type", "sent_to_orchestrator", "company",
    )
    list_filter = ("company", "report_type", "sent_to_orchestrator")
    search_fields = ("code", "summary")
    autocomplete_fields = ("project", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "report_date"
    list_select_related = ("project",)

    actions = ["mark_sent"]

    @admin.action(description=_("Отметить как отправленные в Orchestrator"))
    def mark_sent(self, request, queryset):
        queryset.filter(sent_to_orchestrator=False).update(
            sent_to_orchestrator=True,
            sent_to_orchestrator_at=timezone.now(),
        )