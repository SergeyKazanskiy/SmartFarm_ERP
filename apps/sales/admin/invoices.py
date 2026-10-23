"""Админка счетов."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.sales.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "invoice_number", "order", "invoice_date",
        "due_date", "total_amount", "paid_amount", "status", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "invoice_number")
    autocomplete_fields = ("order", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "invoice_date"
    list_select_related = ("order",)

    actions = ["mark_sent"]

    @admin.action(description=_("Отметить как 'Отправлено'"))
    def mark_sent(self, request, queryset):
        queryset.filter(status="draft").update(status="sent")