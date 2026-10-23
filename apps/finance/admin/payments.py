"""Админка платежей."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.finance.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "invoice", "bank_account", "cash_account",
        "payment_status", "payment_date", "amount", "company",
    )
    list_filter = ("company", "payment_status")
    search_fields = ("code", "invoice__invoice_number")
    autocomplete_fields = ("invoice", "bank_account", "cash_account", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "payment_date"
    list_select_related = ("invoice", "bank_account", "cash_account")

    actions = ["complete_payments", "cancel_payments"]

    @admin.action(description=_("Провести платежи"))
    def complete_payments(self, request, queryset):
        # Бизнес-логику пересчёта статуса счёта выполняет сервис;
        # здесь — только прямое изменение статуса платежа для ручной правки.
        queryset.filter(payment_status="planned").update(payment_status="completed")

    @admin.action(description=_("Отменить платежи"))
    def cancel_payments(self, request, queryset):
        queryset.filter(payment_status="planned").update(payment_status="cancelled")