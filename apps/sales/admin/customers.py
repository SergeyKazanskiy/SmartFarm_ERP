"""Админка клиентов."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.sales.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "counterparty_id", "category",
        "credit_limit", "payment_terms", "is_active", "company",
    )
    list_filter = ("company", "category", "is_active")
    search_fields = ("code",)
    autocomplete_fields = ("default_price_list", "company")
    readonly_fields = ("created_at", "updated_at")

    actions = ["activate", "deactivate"]

    @admin.action(description=_("Активировать"))
    def activate(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description=_("Деактивировать"))
    def deactivate(self, request, queryset):
        queryset.update(is_active=False)