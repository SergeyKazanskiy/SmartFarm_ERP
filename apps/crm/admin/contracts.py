"""Админка договоров."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.crm.models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "contract_number", "counterparty_id",
        "contract_date", "contract_amount", "status", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "contract_number")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "contract_date"

    actions = ["activate_selected", "complete_selected", "terminate_selected"]

    @admin.action(description=_("Активировать договоры"))
    def activate_selected(self, request, queryset):
        queryset.filter(status="draft").update(status="active")

    @admin.action(description=_("Завершить договоры"))
    def complete_selected(self, request, queryset):
        queryset.filter(status="active").update(status="completed")

    @admin.action(description=_("Расторгнуть договоры"))
    def terminate_selected(self, request, queryset):
        queryset.filter(status="active").update(status="terminated")