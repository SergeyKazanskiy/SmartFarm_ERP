"""Админка счетов."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.finance.models import Invoice, InvoiceLine


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    fields = ("code", "description", "amount")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "invoice_number", "invoice_type",
        "counterparty_id", "invoice_date", "due_date",
        "amount", "status", "company",
    )
    list_filter = ("company", "invoice_type", "status")
    search_fields = ("code", "invoice_number", "counterparty_id", "source_object_type")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "invoice_date"
    inlines = [InvoiceLineInline]

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "invoice_type", "invoice_number"),
        }),
        (_("Контрагент и основание"), {
            "fields": (
                "counterparty_id", "contract_id",
                "source_object_type", "source_object_id",
            ),
        }),
        (_("Даты и сумма"), {
            "fields": ("invoice_date", "due_date", "amount", "currency_id"),
        }),
        (_("Статус"), {
            "fields": ("status",),
        }),
        (_("Служебное"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["issue_invoices", "cancel_invoices"]

    @admin.action(description=_("Выставить счета"))
    def issue_invoices(self, request, queryset):
        queryset.filter(status="draft").update(status="issued")

    @admin.action(description=_("Отменить счета"))
    def cancel_invoices(self, request, queryset):
        queryset.filter(status__in=["draft", "issued"]).update(status="cancelled")


@admin.register(InvoiceLine)
class InvoiceLineAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "invoice", "description", "amount", "company")
    list_filter = ("company",)
    search_fields = ("code", "description")
    autocomplete_fields = ("invoice", "company")