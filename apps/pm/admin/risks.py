"""Админка рисков и запросов на изменение."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.pm.models import ChangeRequest, Risk


@admin.register(Risk)
class RiskAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "project", "probability",
        "impact", "severity", "status", "owner_employee_id", "company",
    )
    list_filter = ("company", "status", "severity")
    search_fields = ("code", "name", "description")
    autocomplete_fields = ("project", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("project",)

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "project", "name", "description"),
        }),
        (_("Оценка"), {
            "fields": ("probability", "impact", "severity", "status"),
        }),
        (_("Смягчение"), {
            "fields": ("mitigation_plan", "owner_employee_id"),
        }),
        (_("Служебное"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )


@admin.register(ChangeRequest)
class ChangeRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "title", "project", "change_type", "status",
        "requested_by_employee_id", "approved_by_employee_id", "company",
    )
    list_filter = ("company", "change_type", "status")
    search_fields = ("code", "title", "description")
    autocomplete_fields = ("project", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("project",)

    actions = ["submit_selected", "approve_selected"]

    @admin.action(description=_("Отправить на утверждение"))
    def submit_selected(self, request, queryset):
        queryset.filter(status="draft").update(
            status="submitted", requested_at=timezone.now(),
        )

    @admin.action(description=_("Утвердить изменения"))
    def approve_selected(self, request, queryset):
        queryset.filter(status="submitted").update(
            status="approved", approved_at=timezone.now(),
        )