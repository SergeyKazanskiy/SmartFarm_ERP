"""Чёрный список контрагентов."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.cp.models import Blacklist


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = (
        "id", "counterparty", "block_date", "blocked_by_employee_id",
        "unblock_date", "unblocked_by_employee_id", "company",
    )
    list_filter = ("company", "block_date", "unblock_date")
    search_fields = ("counterparty__name", "counterparty__code", "reason")
    autocomplete_fields = ("counterparty", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "block_date"
    list_select_related = ("counterparty",)