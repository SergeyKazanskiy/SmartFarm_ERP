"""Админка проектов, этапов и вех."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.pm.models import Milestone, Phase, Project


class PhaseInline(admin.TabularInline):
    model = Phase
    fk_name = "project"
    extra = 0
    fields = (
        "code", "name", "order", "status",
        "planned_start_date", "planned_end_date", "completion_percent",
    )


class MilestoneInline(admin.TabularInline):
    model = Milestone
    extra = 0
    fields = ("code", "name", "milestone_date", "is_achieved", "achieved_date")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "status", "priority",
        "planned_start_date", "planned_end_date",
        "project_manager_employee_id", "customer_id", "company",
    )
    list_filter = ("company", "status", "priority")
    search_fields = ("code", "name", "project_code", "orchestrator_id")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "planned_start_date"
    inlines = [PhaseInline, MilestoneInline]

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "name", "project_code", "description"),
        }),
        (_("Источник и заказчик"), {
            "fields": ("orchestrator_id", "customer_id", "project_manager_employee_id"),
        }),
        (_("Даты"), {
            "fields": (
                "planned_start_date", "planned_end_date",
                "actual_start_date", "actual_end_date",
            ),
        }),
        (_("Статус и приоритет"), {
            "fields": ("status", "priority"),
        }),
        (_("Служебное"), {
            "fields": ("created_by_employee_id", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["mark_active", "mark_on_hold", "mark_completed"]

    @admin.action(description=_("Активировать проекты"))
    def mark_active(self, request, queryset):
        queryset.filter(status__in=["planning", "on_hold"]).update(status="active")

    @admin.action(description=_("Приостановить проекты"))
    def mark_on_hold(self, request, queryset):
        queryset.filter(status="active").update(status="on_hold")

    @admin.action(description=_("Завершить проекты"))
    def mark_completed(self, request, queryset):
        queryset.filter(status="active").update(status="completed")


@admin.register(Phase)
class PhaseAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "project", "order", "status",
        "planned_start_date", "planned_end_date", "completion_percent", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "name", "project__name")
    autocomplete_fields = ("project", "parent", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("project",)


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "project", "milestone_date",
        "is_achieved", "achieved_date", "company",
    )
    list_filter = ("company", "is_achieved")
    search_fields = ("code", "name", "project__name")
    autocomplete_fields = ("project", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "milestone_date"