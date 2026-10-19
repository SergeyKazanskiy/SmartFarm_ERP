"""Админка навыков и компетенций."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.hr.models import (
    HREmployeeCompetencyScore, HREmployeeQualification,
    HREmployeeSkill, HRQualification,
)


@admin.register(HREmployeeSkill)
class HREmployeeSkillAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "skill", "self_assessed_level",
        "confirmed_level", "company",
    )
    list_filter = ("company", "skill", "confirmed_level")
    autocomplete_fields = ("employee", "skill", "company")
    search_fields = ("employee__personnel_number", "skill__skill_name")
    list_select_related = ("employee", "skill")


@admin.register(HREmployeeCompetencyScore)
class HREmployeeCompetencyScoreAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "skill", "score_value",
        "evaluated_at", "company",
    )
    list_filter = ("company", "skill")
    autocomplete_fields = ("employee", "skill", "company")
    date_hierarchy = "evaluated_at"


@admin.register(HREmployeeQualification)
class HREmployeeQualificationAdmin(admin.ModelAdmin):
    list_display = ("id", "employee", "qualification", "valid_to", "company")
    list_filter = ("company", "qualification")
    autocomplete_fields = ("employee", "qualification", "company")
    date_hierarchy = "valid_to"