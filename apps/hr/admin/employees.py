"""Админка кадрового учёта."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.hr.models import HREmployee, HREmployeeDocument


class HREmployeeDocumentInline(admin.TabularInline):
    model = HREmployeeDocument
    extra = 0
    autocomplete_fields = ("employee",)
    fields = ("document_id", "document_role")


@admin.register(HREmployee)
class HREmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "id", "personnel_number", "position", "department_id",
        "status", "employment_date", "company",
    )
    list_filter = ("company", "status", "position", "schedule")
    search_fields = ("personnel_number", "natural_person_id")
    autocomplete_fields = ("position", "schedule", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "employment_date"
    list_select_related = ("position", "schedule", "company")
    inlines = [HREmployeeDocumentInline]

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "natural_person_id", "personnel_number"),
        }),
        (_("Должность и подразделение"), {
            "fields": ("position", "department_id", "schedule"),
        }),
        (_("Даты и статус"), {
            "fields": ("employment_date", "dismissal_date", "status"),
        }),
        (_("Служебная информация"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["make_active", "make_suspended"]

    @admin.action(description=_("Установить статус 'Активен'"))
    def make_active(self, request, queryset):
        queryset.update(status="active")

    @admin.action(description=_("Установить статус 'Отстранён'"))
    def make_suspended(self, request, queryset):
        queryset.update(status="suspended")


@admin.register(HREmployeeDocument)
class HREmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "document_id", "document_role", "company")
    list_filter = ("company",)
    autocomplete_fields = ("employee", "company")
    search_fields = ("document_id",)