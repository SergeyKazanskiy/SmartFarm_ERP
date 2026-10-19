from rest_framework import serializers

from apps.tasks.models import (
    TaskAssignment, TaskComment, TaskNotification,
    TaskPhoto, TaskTask, TaskTimeTracking,
)

# Класс сериализатора для списка задач
class TaskListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    priority_display = serializers.SerializerMethodField()

    class Meta:
        model = TaskTask
        fields = [
            "id", "task_name", "status", "status_display",
            "priority", "priority_display",
            "planned_finish", "actual_finish", "completion_percent",
            "assigned_role",
        ]
        read_only_fields = fields

    def get_priority_display(self, obj):
        return obj.priority

# Класс сериализатора для детальной информации о задаче
class TaskDetailSerializer(TaskListSerializer):
    definition_code = serializers.CharField(source="definition.code", read_only=True)
    definition_name = serializers.CharField(source="definition.name", read_only=True)
    form_refs = serializers.JSONField(source="definition.form_refs", read_only=True)
    comments = serializers.SerializerMethodField()
    time_tracking_total = serializers.SerializerMethodField()

    class Meta(TaskListSerializer.Meta):
        fields = TaskListSerializer.Meta.fields + [
            "description", "source_type", "source_id",
            "planned_start", "actual_start",
            "estimated_hours", "actual_hours",
            "definition_code", "definition_name", "form_refs",
            "comments", "time_tracking_total",
        ]

    def get_comments(self, obj):
        qs = obj.comments.all()[:50]
        return TaskCommentSerializer(qs, many=True).data

    def get_time_tracking_total(self, obj):
        from django.db.models import Sum
        result = obj.time_tracking.aggregate(total=Sum("hours"))
        return float(result["total"] or 0)

# Класс сериализатора для комментариев к задаче
class TaskCommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskComment
        fields = ["id", "comment_text", "employee_id", "created_at"]
        read_only_fields = ["id", "employee_id", "created_at"]

# Класс сериализатора для трекинга времени по задаче
class TaskTimeTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskTimeTracking
        fields = ["id", "date_logged", "hours", "description", "employee_id", "created_at"]
        read_only_fields = ["id", "employee_id", "created_at"]

# Класс сериализатора для фотографий, связанных с задачей
class TaskPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskPhoto
        fields = ["id", "photo", "description", "employee_id", "created_at"]
        read_only_fields = ["id", "employee_id", "created_at"]

# Класс сериализатора для уведомлений о задачах
class TaskNotificationSerializer(serializers.ModelSerializer):
    task_name = serializers.CharField(source="task.task_name", read_only=True)
    type_display = serializers.CharField(source="get_notification_type_display", read_only=True)

    class Meta:
        model = TaskNotification
        fields = [
            "id", "task", "task_name", "notification_type", "type_display",
            "message", "is_read", "sent_at", "read_at",
        ]
        read_only_fields = fields

# Класс сериализатора для назначения задач сотрудникам
class TaskAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAssignment
        fields = [
            "id", "task", "employee_id", "role_id",
            "status", "assigned_at", "started_at", "finished_at",
        ]
        read_only_fields = ["id", "assigned_at", "started_at", "finished_at"]