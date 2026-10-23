"""Админка справочников Finance: план счетов, ЦЗ, финпроекты, кассы, банк-счета, курсы."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.finance.models import (
    BankAccount, CashAccount, CostCenter, ExchangeRate, FinAccount,
    FinancialProject,
)


@admin.register(FinAccount)
class FinAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "account_code", "account_name", "account_type", "company")
    list_filter = ("company", "account_type")
    search_fields = ("code", "account_code", "account_name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


@admin.register(FinancialProject)
class FinancialProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "linked_object_type", "linked_object_id", "company",
    )
    list_filter = ("company", "linked_object_type")
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


@admin.register(CashAccount)
class CashAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "account_number", "bank_id", "currency_id", "company")
    list_filter = ("company",)
    search_fields = ("code", "account_number")
    autocomplete_fields = ("company",)


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "currency_id", "rate_date", "rate_value", "company")
    list_filter = ("company", "currency_id")
    search_fields = ("code",)
    autocomplete_fields = ("company",)
    date_hierarchy = "rate_date"