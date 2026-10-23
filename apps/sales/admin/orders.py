"""Админка заказов."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.sales.models import Order, OrderLine


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    fields = (
        "code", "material_id", "quantity", "unit_price",
        "discount_percent", "total_price", "shipped_quantity",
    )
    readonly_fields = ("total_price", "shipped_quantity")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "order_number", "customer", "order_date",
        "status", "total_amount", "expected_ship_date", "company",
    )
    list_filter = ("company", "status", "order_type")
    search_fields = ("code", "order_number")
    autocomplete_fields = ("customer", "quote", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "order_date"
    list_select_related = ("customer", "quote")
    inlines = [OrderLineInline]

    actions = ["confirm_orders", "cancel_orders"]

    @admin.action(description=_("Подтвердить заказы"))
    def confirm_orders(self, request, queryset):
        queryset.filter(status="draft").update(status="confirmed")

    @admin.action(description=_("Отменить заказы"))
    def cancel_orders(self, request, queryset):
        queryset.filter(status__in=["draft", "confirmed"]).update(status="cancelled")


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "order", "material_id",
        "quantity", "unit_price", "discount_percent",
        "total_price", "shipped_quantity", "company",
    )
    list_filter = ("company",)
    autocomplete_fields = ("order", "company")
    readonly_fields = ("total_price", "shipped_quantity")