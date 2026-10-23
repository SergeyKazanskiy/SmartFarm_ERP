"""Админка контактных лиц CRM."""
from django.contrib import admin

from apps.crm.models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "position", "phone", "email", "counterparty_id", "company")
    list_filter = ("company",)
    search_fields = ("code", "position", "phone", "email")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")