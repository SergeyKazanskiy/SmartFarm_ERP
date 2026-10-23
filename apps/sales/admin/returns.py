"""Админка возвратов."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.sales.models import Return, ReturnLine


class ReturnLineInline(admin.TabularInline):
    model = ReturnLine
    extra = 0
    fields = ("code", "order_line", "quantity")


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "return_number", "order", "return_date",
        "status", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "return_number")
    autocomplete_fields = ("order", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "return_date"
    list_select_related = ("order",)
    inlines = [ReturnLineInline]

    actions = ["approve_returns", "mark_received"]

    @admin.action(description=_("Утвердить возвраты"))
    def approve_returns(self, request, queryset):
        queryset.filter(status="draft").update(status="approved")

    @admin.action(description=_("Отметить как 'Получено'"))
    def mark_received(self, request, queryset):
        queryset.filter(status="approved").update(status="received")


@admin.register(ReturnLine)
class ReturnLineAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "return_", "order_line", "quantity", "company")
    list_filter = ("company",)
    autocomplete_fields = ("return_", "order_line", "company")