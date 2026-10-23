"""
DRF-сериализаторы PM.
"""
from rest_framework import serializers

from apps.pm.models import (
    Budget, BudgetItem, ChangeRequest, Milestone, Phase, Project,
    Report, ResourceNeed, Risk, StatusHistory, Task, TaskDependency,
)


class ProjectListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "code", "name", "project_code",
            "status", "status_display", "priority",
            "planned_start_date", "planned_end_date",
            "customer_id", "project_manager_employee_id",
        ]


class ProjectDetailSerializer(ProjectListSerializer):
    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + [
            "description", "orchestrator_id",
            "actual_start_date", "actual_end_date",
            "created_at", "updated_at",
        ]


class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            "code", "name", "project_code", "description",
            "orchestrator_id", "customer_id", "project_manager_employee_id",
            "planned_start_date", "planned_end_date", "priority",
        ]


class PhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phase
        fields = [
            "id", "code", "project", "parent", "name", "order",
            "planned_start_date", "planned_end_date",
            "actual_start_date", "actual_end_date",
            "status", "completion_percent",
        ]
        read_only_fields = ["actual_start_date", "actual_end_date"]


class MilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Milestone
        fields = [
            "id", "code", "project", "name", "milestone_date",
            "is_achieved", "achieved_date", "description",
        ]
        read_only_fields = ["is_achieved", "achieved_date"]


class TaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Task
        fields = [
            "id", "code", "project", "phase", "parent",
            "name", "description",
            "planned_start_date", "planned_end_date",
            "actual_start_date", "actual_end_date",
            "status", "status_display", "completion_percent", "priority",
            "assignee_employee_id",
        ]
        read_only_fields = ["actual_start_date", "actual_end_date", "completion_percent"]


class TaskDependencySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDependency
        fields = [
            "id", "code", "predecessor", "successor",
            "dependency_type", "lag_days",
        ]


class ResourceNeedSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResourceNeed
        fields = [
            "id", "code", "task", "resource_type",
            "role_id", "skill_id", "quantity", "unit_id",
            "hours_per_day", "days_required", "priority",
            "sent_to_aps", "sent_to_aps_at",
        ]
        read_only_fields = ["sent_to_aps", "sent_to_aps_at"]


class BudgetItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetItem
        fields = [
            "id", "code", "budget", "category",
            "planned_amount", "actual_amount", "description",
        ]


class BudgetSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = BudgetItemSerializer(many=True, read_only=True)

    class Meta:
        model = Budget
        fields = [
            "id", "code", "project", "name",
            "total_planned_amount", "total_actual_amount",
            "currency_id", "status", "status_display",
            "approved_by_employee_id", "approved_at",
            "items",
        ]
        read_only_fields = ["approved_by_employee_id", "approved_at"]


class RiskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Risk
        fields = [
            "id", "code", "project", "name", "description",
            "probability", "impact", "severity",
            "mitigation_plan", "status", "status_display",
            "owner_employee_id",
        ]
        read_only_fields = ["severity"]


class ChangeRequestSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ChangeRequest
        fields = [
            "id", "code", "project", "title", "description",
            "change_type", "impact_description",
            "status", "status_display",
            "requested_by_employee_id", "approved_by_employee_id",
            "requested_at", "approved_at",
        ]
        read_only_fields = [
            "requested_by_employee_id", "approved_by_employee_id",
            "requested_at", "approved_at",
        ]


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusHistory
        fields = [
            "id", "project", "status_from", "status_to",
            "changed_by_employee_id", "changed_at", "comment",
        ]
        read_only_fields = ["changed_at", "changed_by_employee_id"]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id", "code", "project", "report_date", "report_type",
            "summary",
            "status_summary_json", "budget_summary_json",
            "schedule_summary_json", "risks_summary_json",
            "sent_to_orchestrator", "sent_to_orchestrator_at",
        ]
        read_only_fields = fields