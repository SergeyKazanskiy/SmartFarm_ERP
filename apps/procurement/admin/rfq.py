"""Админка RFQ."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.procurement.models import RFQ, RFQSupplier, SupplierQuote


class RFQSupplierInline(admin.TabularInline):
    model = RFQSupplier
    extra = 0
    fields = ("code", "supplier")
    autocomplete_fields = ("supplier",)


@admin.register(RFQ)
class RFQAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "rfq_number", "requisition",
        "rfq_date", "response_deadline", "status", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "rfq_number")
    autocomplete_fields = ("requisition", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "rfq_date"
    list_select_related = ("requisition",)
    inlines = [RFQSupplierInline]

    actions = ["send_rfqs", "close_rfqs"]

    @admin.action(description=_("Отправить RFQ"))
    def send_rfqs(self, request, queryset):
        queryset.filter(status="draft").update(status="sent")

    @admin.action(description=_("Закрыть RFQ"))
    def close_rfqs(self, request, queryset):
        queryset.filter(status__in=["sent", "responded"]).update(status="closed")


@admin.register(RFQSupplier)
class RFQSupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "rfq", "supplier", "company")
    list_filter = ("company",)
    autocomplete_fields = ("rfq", "supplier", "company")


@admin.register(SupplierQuote)
class SupplierQuoteAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "rfq_supplier", "material_id",
        "unit_price", "quantity", "delivery_days", "company",
    )
    list_filter = ("company",)
    autocomplete_fields = ("rfq_supplier", "company")