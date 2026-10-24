"""Админка производственных заказов."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.production.models import ProductionOrder


@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "bom", "routing", "planned_quantity",
        "planned_start_date", "planned_end_date",
        "status", "company",
    )
    list_filter = ("company", "status", "bom", "routing")
    search_fields = ("code",)
    autocomplete_fields = ("bom", "routing", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "planned_start_date"
    list_select_related = ("bom", "routing")

    actions = ["confirm_orders", "start_orders", "complete_orders", "cancel_orders"]

    @admin.action(description=_("Подтвердить заказы"))
    def confirm_orders(self, request, queryset):
        queryset.filter(status="draft").update(status="confirmed")

    @admin.action(description=_("Запустить в производство"))
    def start_orders(self, request, queryset):
        queryset.filter(status="confirmed").update(status="in_progress")

    @admin.action(description=_("Закрыть заказы"))
    def complete_orders(self, request, queryset):
        queryset.filter(status="in_progress").update(status="completed")

    @admin.action(description=_("Отменить заказы"))
    def cancel_orders(self, request, queryset):
        queryset.filter(status__in=["draft", "confirmed"]).update(status="cancelled")