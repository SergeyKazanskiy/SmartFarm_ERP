"""Админка отсутствий."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.hr.models import HREmployeeAbsence


@admin.register(HREmployeeAbsence)
class HREmployeeAbsenceAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "absence_type", "date_from", "date_to",
        "status", "company",
    )
    list_filter = ("company", "status", "absence_type")
    autocomplete_fields = ("employee", "absence_type", "company")
    date_hierarchy = "date_from"
    list_select_related = ("employee", "absence_type")
    actions = ["approve_selected", "reject_selected"]

    @admin.action(description=_("Согласовать выбранные заявки"))
    def approve_selected(self, request, queryset):
        queryset.filter(status="requested").update(status="approved")

    @admin.action(description=_("Отклонить выбранные заявки"))
    def reject_selected(self, request, queryset):
        queryset.filter(status="requested").update(status="rejected")