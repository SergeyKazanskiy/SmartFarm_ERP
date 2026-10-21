"""Договоры и прикреплённые документы."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.cp.models import Attachment, Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "contract_number", "counterparty",
        "contract_type", "amount", "status",
        "valid_from", "valid_to", "company",
    )
    list_filter = ("company", "status", "contract_type")
    search_fields = ("code", "contract_number", "counterparty__name")
    autocomplete_fields = ("counterparty", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "contract_date"
    list_select_related = ("counterparty",)

    actions = ["activate_selected", "terminate_selected"]

    @admin.action(description=_("Активировать договоры"))
    def activate_selected(self, request, queryset):
        queryset.filter(status="draft").update(status="active")

    @admin.action(description=_("Расторгнуть договоры"))
    def terminate_selected(self, request, queryset):
        queryset.filter(status="active").update(status="terminated")


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "counterparty", "document_id",
        "attachment_type", "created_by_employee_id", "company",
    )
    list_filter = ("company", "attachment_type")
    search_fields = ("code", "document_id", "counterparty__name")
    autocomplete_fields = ("counterparty", "company")
    readonly_fields = ("created_at", "updated_at")