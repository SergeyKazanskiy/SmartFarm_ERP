"""Админка допусков и безопасности."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.hr.models import (
    HRDrivingLicense, HREmployeeCertificate, HRMedicalCheck,
)


@admin.register(HREmployeeCertificate)
class HREmployeeCertificateAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "certificate", "certificate_number",
        "issue_date", "expire_date", "company",
    )
    list_filter = ("company", "certificate")
    autocomplete_fields = ("employee", "certificate", "company")
    search_fields = ("certificate_number",)
    date_hierarchy = "expire_date"


@admin.register(HRMedicalCheck)
class HRMedicalCheckAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "examination_date", "valid_to",
        "result", "company",
    )
    list_filter = ("company", "result")
    autocomplete_fields = ("employee", "company")
    date_hierarchy = "examination_date"


@admin.register(HRDrivingLicense)
class HRDrivingLicenseAdmin(admin.ModelAdmin):
    list_display = (
        "id", "employee", "license_number", "categories",
        "valid_to", "company",
    )
    list_filter = ("company", "categories")
    autocomplete_fields = ("employee", "company")
    search_fields = ("license_number",)
    date_hierarchy = "valid_to"