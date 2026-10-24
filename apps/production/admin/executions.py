"""Админка нарядов и выполнения операций."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.production.models import OperationExecution, WorkOrder


class ExecutionInline(admin.TabularInline):
    model = OperationExecution
    extra = 0
    fields = (
        "code", "operation", "work_center", "performed_by_employee_id",
        "start_time", "end_time", "status",
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "production_order", "status",
        "planned_start", "planned_finish",
        "actual_start", "actual_finish", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code",)
    autocomplete_fields = ("production_order", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "planned_start"
    list_select_related = ("production_order",)
    inlines = [ExecutionInline]

    actions = ["start_orders", "hold_orders", "resume_orders", "complete_orders", "cancel_orders"]

    @admin.action(description=_("Запустить наряд"))
    def start_orders(self, request, queryset):
        queryset.filter(status="planned").update(
            status="in_progress", actual_start=timezone.now(),
        )

    @admin.action(description=_("Приостановить"))
    def hold_orders(self, request, queryset):
        queryset.filter(status="in_progress").update(status="on_hold")

    @admin.action(description=_("Возобновить"))
    def resume_orders(self, request, queryset):
        queryset.filter(status="on_hold").update(status="in_progress")

    @admin.action(description=_("Завершить"))
    def complete_orders(self, request, queryset):
        queryset.filter(status__in=["in_progress", "on_hold"]).update(
            status="completed", actual_finish=timezone.now(),
        )

    @admin.action(description=_("Отменить"))
    def cancel_orders(self, request, queryset):
        queryset.filter(status="planned").update(status="cancelled")


@admin.register(OperationExecution)
class OperationExecutionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "work_order", "operation", "work_center",
        "performed_by_employee_id", "start_time", "end_time",
        "status", "company",
    )
    list_filter = ("company", "status", "work_center")
    search_fields = ("code",)
    autocomplete_fields = ("work_order", "operation", "work_center", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "start_time"
    list_select_related = ("work_order", "operation", "work_center")

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "work_order", "operation", "work_center"),
        }),
        (_("Исполнение"), {
            "fields": (
                "performed_by_employee_id",
                "start_time", "end_time", "status",
            ),
        }),
        (_("JSON-результаты"), {
            "fields": ("measurements_json", "quality_results_json"),
        }),
        (_("Служебное"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["complete_executions", "send_to_rework"]

    @admin.action(description=_("Завершить выполнения"))
    def complete_executions(self, request, queryset):
        queryset.filter(status="in_progress").update(
            status="completed", end_time=timezone.now(),
        )

    @admin.action(description=_("Вернуть на доработку"))
    def send_to_rework(self, request, queryset):
        queryset.filter(status="completed").update(status="rework", end_time=None)