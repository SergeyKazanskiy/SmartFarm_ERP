"""
DRF-сериализаторы для мобильного приложения (React Native).
Логика: минимум полей, только то, что нужно сотруднику.
"""
from rest_framework import serializers

from apps.hr.models import (
    HREmployee, HREmployeeAbsence, HREmployeeCertificate,
    HREmployeeSkill, HRTimesheet,
)


class HREmployeeShortSerializer(serializers.ModelSerializer):
    position_name = serializers.CharField(source="position.position_name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HREmployee
        fields = [
            "id", "personnel_number", "position_name",
            "status", "status_display", "employment_date",
        ]


class HREmployeeSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source="skill.skill_name", read_only=True)

    class Meta:
        model = HREmployeeSkill
        fields = [
            "id", "skill_name", "self_assessed_level",
            "confirmed_level",
        ]


class HREmployeeCertificateSerializer(serializers.ModelSerializer):
    certificate_name = serializers.CharField(
        source="certificate.certificate_name", read_only=True,
    )

    class Meta:
        model = HREmployeeCertificate
        fields = [
            "id", "certificate_name", "certificate_number",
            "issue_date", "expire_date",
        ]


class HRAbsenceSerializer(serializers.ModelSerializer):
    absence_type_name = serializers.CharField(
        source="absence_type.absence_type_name", read_only=True,
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HREmployeeAbsence
        fields = [
            "id", "absence_type", "absence_type_name",
            "date_from", "date_to", "status", "status_display",
        ]
        read_only_fields = ["status"]


class HRTimesheetSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = HRTimesheet
        fields = [
            "id", "work_date", "hours_worked", "overtime_hours",
            "task_id", "status", "status_display",
        ]
        read_only_fields = ["status"]