"""Админка бухгалтерских проводок."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.finance.models import FinancialTransaction


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "debit_account", "credit_account",
        "cost_center", "payment", "amount", "transaction_date", "company",
    )
    list_filter = ("company", "debit_account", "credit_account", "cost_center")
    search_fields = ("code",)
    autocomplete_fields = ("debit_account", "credit_account", "cost_center", "payment", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "transaction_date"
    list_select_related = ("debit_account", "credit_account", "payment")

    fieldsets = (
        (_("Проводка"), {
            "fields": ("company", "code", "debit_account", "credit_account"),
        }),
        (_("Аналитика"), {
            "fields": ("cost_center", "payment"),
        }),
        (_("Сумма и дата"), {
            "fields": ("amount", "transaction_date"),
        }),
        (_("Служебное"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )