"""Админка заказов поставщикам."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.procurement.models import (
    Delivery, Order, OrderHistory, OrderLine,
)


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    fields = (
        "code", "material_id", "quantity",
        "unit_price", "total_price", "received_quantity",
    )
    readonly_fields = ("total_price", "received_quantity")


class OrderHistoryInline(admin.TabularInline):
    model = OrderHistory
    extra = 0
    fields = (
        "code", "changed_at", "status_from", "status_to",
        "changed_by_employee_id", "comment",
    )
    readonly_fields = ("changed_at",)
    can_delete = False


class DeliveryInline(admin.TabularInline):
    model = Delivery
    extra = 0
    fields = ("code", "delivery_date", "quantity", "status")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "order_number", "supplier",
        "order_date", "expected_delivery_date", "actual_delivery_date",
        "status", "total_amount", "company",
    )
    list_filter = ("company", "status", "supplier")
    search_fields = ("code", "order_number")
    autocomplete_fields = ("supplier", "requisition", "rfq", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "order_date"
    list_select_related = ("supplier",)
    inlines = [OrderLineInline, DeliveryInline, OrderHistoryInline]

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "order_number", "supplier"),
        }),
        (_("Основание"), {
            "fields": ("requisition", "rfq"),
        }),
        (_("Даты"), {
            "fields": (
                "order_date", "expected_delivery_date", "actual_delivery_date",
            ),
        }),
        (_("Сумма и статус"), {
            "fields": ("status", "total_amount", "currency_id"),
        }),
        (_("Служебное"), {
            "fields": ("created_by_employee_id", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["send_orders", "confirm_orders", "cancel_orders"]

    @admin.action(description=_("Отправить заказы поставщикам"))
    def send_orders(self, request, queryset):
        queryset.filter(status="draft").update(status="sent")

    @admin.action(description=_("Подтвердить заказы"))
    def confirm_orders(self, request, queryset):
        queryset.filter(status="sent").update(status="confirmed")

    @admin.action(description=_("Отменить заказы"))
    def cancel_orders(self, request, queryset):
        queryset.filter(status__in=["draft", "sent"]).update(status="cancelled")


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "order", "material_id",
        "quantity", "unit_price", "total_price",
        "received_quantity", "company",
    )
    list_filter = ("company",)
    autocomplete_fields = ("order", "company")
    readonly_fields = ("total_price", "received_quantity")


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "order", "delivery_date",
        "quantity", "status", "company",
    )
    list_filter = ("company", "status")
    autocomplete_fields = ("order", "company")
    date_hierarchy = "delivery_date"


@admin.register(OrderHistory)
class OrderHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "order", "status_from", "status_to",
        "changed_by_employee_id", "changed_at", "company",
    )
    list_filter = ("company", "status_to")
    autocomplete_fields = ("order", "company")
    readonly_fields = ("changed_at",)
    date_hierarchy = "changed_at"