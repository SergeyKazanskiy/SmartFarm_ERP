from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, User


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "tax_id", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "tax_id")
    readonly_fields = ("uuid", "created_at", "updated_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("email", "username", "full_name", "is_active", "current_company")
    list_filter = ("is_active", "is_staff", "current_company")
    search_fields = ("email", "username", "full_name")
    ordering = ("email",)
    filter_horizontal = ("companies", "groups", "user_permissions")

    fieldsets = BaseUserAdmin.fieldsets + (
        (_("ERP"), {"fields": (
            "full_name", "companies", "current_company",
            "hr_employee_id", "preferred_language",
        )}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("ERP"), {"fields": (
            "email", "full_name", "preferred_language",
        )}),
    )

# Локализация заголовков и названий в админке ???
admin.site.site_header = _("ERP Administration")
admin.site.site_title = _("ERP")
admin.site.index_title = _("Control Panel")