"""
Админка TASK-модуля: «Мои задачи» + динамические формы операций.
"""
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.dynamic_forms import BusinessFormFactory

from apps.tasks.models import (
    ProcessTaskDefinition, ProcessTaskTransition, TaskAssignment,
    TaskAttachment, TaskComment, TaskDependency, TaskNotification,
    TaskPhoto, TaskStatusHistory, TaskTask, TaskTimeTracking,
)


@admin.register(ProcessTaskDefinition)
class ProcessTaskDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "code", "module", "process_code", "name", "role",
        "is_active", "company",
    )
    list_filter = ("module", "role", "is_active", "company")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProcessTaskTransition)
class ProcessTaskTransitionAdmin(admin.ModelAdmin):
    list_display = ("source", "target", "condition", "company")
    list_filter = ("company",)
    autocomplete_fields = ("source", "target", "company")


class TaskAssignmentInline(admin.TabularInline):
    model = TaskAssignment
    extra = 0
    fields = ("employee_id", "role_id", "status", "started_at", "finished_at")
    readonly_fields = ("started_at", "finished_at")


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    fields = ("employee_id", "comment_text")


@admin.register(TaskTask)
class TaskTaskAdmin(admin.ModelAdmin):
    list_display = (
        "id", "task_name", "assigned_role", "status",
        "priority", "planned_finish", "company",
    )
    list_filter = ("company", "status", "assigned_role", "source_type")
    search_fields = ("task_name", "description")
    autocomplete_fields = ("definition", "company")
    readonly_fields = ("created_at", "updated_at", "actual_start", "actual_finish")
    date_hierarchy = "created_at"
    inlines = [TaskAssignmentInline, TaskCommentInline]

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "definition", "task_name", "description"),
        }),
        (_("Источник"), {
            "fields": ("source_type", "source_id", "project_id", "assigned_role"),
        }),
        (_("Статус и время"), {
            "fields": (
                "status", "completion_percent", "priority", "work_type",
                "planned_start", "planned_finish",
                "actual_start", "actual_finish",
                "estimated_hours", "actual_hours",
            ),
        }),
        (_("Служебное"), {
            "fields": ("created_by_employee_id", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    # Кастомные URL для выполнения операции по задаче
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:task_id>/execute/<str:op_code>/",
                self.admin_site.admin_view(self.execute_operation_view),
                name="tasks_tasktask_execute_operation",
            ),
        ]
        return custom + urls

    def execute_operation_view(self, request, task_id: int, op_code: str):
        """
        Отображает форму операции из YAML и обрабатывает её отправку.
        """
        task = TaskTask.objects.get(pk=task_id)

        try:
            FormClass = BusinessFormFactory.get_form(op_code)
        except ValueError as e:
            messages.error(request, str(e))
            return HttpResponseRedirect(
                reverse("admin:tasks_tasktask_change", args=[task_id])
            )

        if request.method == "POST":
            form = FormClass(request.POST, request.FILES, user=request.user)
            if form.is_valid():
                instance = form.save(commit=False)
                # Дозаполняем обязательные поля
                if hasattr(instance, "company_id"):
                    instance.company_id = task.company_id
                if hasattr(instance, "task_id") and not instance.task_id:
                    instance.task_id = task.id
                instance.save()
                messages.success(request, _("Операция выполнена"))
                return HttpResponseRedirect(
                    reverse("admin:tasks_tasktask_change", args=[task_id])
                )
        else:
            initial = {"task_id": task.id, "task": task.id}
            form = FormClass(initial=initial, user=request.user)

        context = {
            **self.admin_site.each_context(request),
            "title": _("Выполнение операции %(op)s") % {"op": op_code},
            "form": form,
            "task": task,
            "op_code": op_code,
        }
        from django.shortcuts import render
        return render(request, "admin/tasks/execute_operation.html", context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        """
        Добавляем в контекст доступные операции для задачи
        (на основе form_refs из определения).
        """
        extra_context = extra_context or {}
        task = TaskTask.objects.filter(pk=object_id).first()
        if task and task.definition:
            extra_context["available_operations"] = task.definition.form_refs
        return super().change_view(request, object_id, form_url, extra_context)


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "task", "employee_id", "status",
        "assigned_at", "started_at", "finished_at", "company",
    )
    list_filter = ("company", "status")
    autocomplete_fields = ("task", "company")
    date_hierarchy = "assigned_at"


@admin.register(TaskNotification)
class TaskNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "task", "employee_id", "notification_type",
        "is_read", "sent_at", "company",
    )
    list_filter = ("company", "notification_type", "is_read")
    autocomplete_fields = ("task", "company")
    actions = ["mark_read"]

    @admin.action(description=_("Отметить как прочитанные"))
    def mark_read(self, request, queryset):
        queryset.update(is_read=True, read_at=timezone.now())


@admin.register(TaskTimeTracking)
class TaskTimeTrackingAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "employee_id", "date_logged", "hours", "company")
    list_filter = ("company", "date_logged")
    autocomplete_fields = ("task", "company")


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "employee_id", "created_at", "company")
    autocomplete_fields = ("task", "company")


@admin.register(TaskPhoto)
class TaskPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "employee_id", "created_at", "company")
    autocomplete_fields = ("task", "company")


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "task", "document_id", "created_at", "company")
    autocomplete_fields = ("task", "company")


@admin.register(TaskDependency)
class TaskDependencyAdmin(admin.ModelAdmin):
    list_display = (
        "id", "predecessor", "successor", "dependency_type",
        "lag_days", "company",
    )
    list_filter = ("company", "dependency_type")
    autocomplete_fields = ("predecessor", "successor", "company")


@admin.register(TaskStatusHistory)
class TaskStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "task", "status_from", "status_to",
        "changed_by_employee_id", "created_at", "company",
    )
    list_filter = ("company", "status_to")
    autocomplete_fields = ("task", "company")