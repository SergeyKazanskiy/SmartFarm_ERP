from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from apps.companies.models import Company, User


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "tax_id", "is_active", "created_at",)
    list_display_links = ("name",)

    list_filter = ("is_active",)
    search_fields = ("name", "short_name", "tax_id")

    ordering = ("name",)
    date_hierarchy = "created_at"
    list_per_page = 25

    readonly_fields = ("uuid", "created_at", "updated_at")

# class CompanyAdmin(admin.ModelAdmin):
#     list_display = ("name", "short_name", "tax_id", "is_active", "created_at")
#     list_filter = ("is_active",)
#     search_fields = ("name", "tax_id")
#     readonly_fields = ("uuid", "created_at", "updated_at")

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "email",
        "first_name",
        "username",
        "current_company",
        "is_active",
        "is_staff",
    )

    list_display_links = ("email",)
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "preferred_language",
        "current_company",
    )

    search_fields = (
        "email",
        "username",
        "full_name",
        "first_name",
        "last_name",
    )

    ordering = ("email",)
    readonly_fields = ("last_login", "date_joined")
    list_per_page = 25
    filter_horizontal = ("companies", "groups", "user_permissions")

    fieldsets = BaseUserAdmin.fieldsets + (
        (_("ERP"), {"fields": (
            "full_name", "companies", "current_company",
            "hr_employee_id", "preferred_language",
        )}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_("ERP"), {"fields": (
            "email", "full_name", "preferred_language", "companies", "current_company",
        )}),
    )

# Локализация заголовков и названий в админке ???
admin.site.site_header = _("ERP Administration")
admin.site.site_title = _("ERP")
admin.site.index_title = _("Control Panel")