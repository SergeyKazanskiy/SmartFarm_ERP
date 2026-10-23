"""Админка задач и зависимостей."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.pm.models import Task, TaskDependency


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "project", "phase", "status",
        "priority", "completion_percent", "assignee_employee_id", "company",
    )
    list_filter = ("company", "status", "priority")
    search_fields = ("code", "name", "project__name")
    autocomplete_fields = ("project", "phase", "parent", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "planned_start_date"
    list_select_related = ("project", "phase")

    actions = ["mark_in_progress", "mark_completed"]

    @admin.action(description=_("Перевести в 'В работе'"))
    def mark_in_progress(self, request, queryset):
        queryset.filter(status="planned").update(status="in_progress")

    @admin.action(description=_("Завершить задачи"))
    def mark_completed(self, request, queryset):
        queryset.filter(status="in_progress").update(
            status="completed", completion_percent=100,
        )


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "predecessor", "successor",
        "dependency_type", "lag_days", "company",
    )
    list_filter = ("company", "dependency_type")
    autocomplete_fields = ("predecessor", "successor", "company")
    search_fields = ("code",)