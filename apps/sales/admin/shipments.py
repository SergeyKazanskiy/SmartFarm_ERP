"""Админка отгрузок."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.sales.models import Shipment, ShipmentLine


class ShipmentLineInline(admin.TabularInline):
    model = ShipmentLine
    extra = 0
    fields = ("code", "order_line", "quantity")


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "shipment_number", "order", "warehouse_id",
        "shipment_date", "status", "tracking_number", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "shipment_number", "tracking_number")
    autocomplete_fields = ("order", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "shipment_date"
    list_select_related = ("order",)
    inlines = [ShipmentLineInline]

    actions = ["mark_shipped", "mark_delivered"]

    @admin.action(description=_("Отметить как 'Отгружено'"))
    def mark_shipped(self, request, queryset):
        queryset.filter(status="planned").update(status="shipped")

    @admin.action(description=_("Отметить как 'Доставлено'"))
    def mark_delivered(self, request, queryset):
        queryset.filter(status="shipped").update(status="delivered")


@admin.register(ShipmentLine)
class ShipmentLineAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "shipment", "order_line", "quantity", "company")
    list_filter = ("company",)
    autocomplete_fields = ("shipment", "order_line", "company")