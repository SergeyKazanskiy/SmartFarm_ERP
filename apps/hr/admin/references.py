"""Админка справочников HR: должности, графики, навыки, квалификации, сертификаты."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.hr.models import (
    HRAbsenceType, HRCertificate, HRPosition, HRPositionCategory,
    HRQualification, HRSkill, HRSkillGroup, HRWorkSchedule,
)


@admin.register(HRPositionCategory)
class HRPositionCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "category_name", "company", "created_at")
    list_filter = ("company",)
    search_fields = ("category_name",)
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company",)


@admin.register(HRPosition)
class HRPositionAdmin(admin.ModelAdmin):
    list_display = ("id", "position_name", "category", "company")
    list_filter = ("company", "category")
    search_fields = ("position_name",)
    autocomplete_fields = ("category", "company")
    readonly_fields = ("created_at", "updated_at")


@admin.register(HRWorkSchedule)
class HRWorkScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "schedule_name", "schedule_type", "company")
    list_filter = ("company", "schedule_type")
    search_fields = ("schedule_name",)
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(HRSkillGroup)
class HRSkillGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "skill_group_name", "company")
    list_filter = ("company",)
    search_fields = ("skill_group_name",)
    autocomplete_fields = ("company",)


@admin.register(HRSkill)
class HRSkillAdmin(admin.ModelAdmin):
    list_display = ("id", "skill_name", "skill_group", "requires_certificate", "company")
    list_filter = ("company", "requires_certificate", "skill_group")
    search_fields = ("skill_name",)
    autocomplete_fields = ("skill_group", "company")


@admin.register(HRQualification)
class HRQualificationAdmin(admin.ModelAdmin):
    list_display = ("id", "qualification_name", "company")
    list_filter = ("company",)
    search_fields = ("qualification_name",)
    autocomplete_fields = ("company",)


@admin.register(HRCertificate)
class HRCertificateAdmin(admin.ModelAdmin):
    list_display = ("id", "certificate_name", "certificate_type", "company")
    list_filter = ("company", "certificate_type")
    search_fields = ("certificate_name",)
    autocomplete_fields = ("company",)


@admin.register(HRAbsenceType)
class HRAbsenceTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "absence_type_name", "company")
    list_filter = ("company",)
    search_fields = ("absence_type_name",)
    autocomplete_fields = ("company",)