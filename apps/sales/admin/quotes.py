"""Админка КП."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.sales.models import Quote, QuoteLine


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 0
    fields = (
        "code", "material_id", "price_list_item",
        "quantity", "unit_price", "discount_percent", "total_price",
    )
    readonly_fields = ("total_price",)


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "quote_number", "customer", "opportunity",
        "quote_date", "total_amount", "status", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "quote_number")
    autocomplete_fields = ("customer", "opportunity", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "quote_date"
    list_select_related = ("customer",)
    inlines = [QuoteLineInline]

    actions = ["mark_sent"]

    @admin.action(description=_("Отметить как отправленные"))
    def mark_sent(self, request, queryset):
        queryset.filter(status="draft").update(status="sent")


@admin.register(QuoteLine)
class QuoteLineAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "quote", "material_id",
        "quantity", "unit_price", "discount_percent", "total_price", "company",
    )
    list_filter = ("company", "quote")
    autocomplete_fields = ("quote", "price_list_item", "company")
    readonly_fields = ("total_price",)