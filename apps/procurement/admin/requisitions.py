"""Админка заявок на закупку."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.procurement.models import Requisition, RequisitionLine


class RequisitionLineInline(admin.TabularInline):
    model = RequisitionLine
    extra = 0
    fields = ("code", "material_id", "quantity", "unit_id", "estimated_unit_cost")


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "requisition_number", "source_type",
        "requisition_date", "required_date", "status",
        "requested_by_employee_id", "company",
    )
    list_filter = ("company", "status", "source_type")
    search_fields = ("code", "requisition_number")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "requisition_date"
    inlines = [RequisitionLineInline]

    actions = ["submit_to_review", "approve_requisitions", "reject_requisitions"]

    @admin.action(description=_("Отправить на согласование"))
    def submit_to_review(self, request, queryset):
        queryset.filter(status="draft").update(status="pending_approval")

    @admin.action(description=_("Утвердить заявки"))
    def approve_requisitions(self, request, queryset):
        queryset.filter(status="pending_approval").update(status="approved")

    @admin.action(description=_("Отклонить заявки"))
    def reject_requisitions(self, request, queryset):
        queryset.filter(status="pending_approval").update(status="rejected")


@admin.register(RequisitionLine)
class RequisitionLineAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "requisition", "material_id",
        "quantity", "unit_id", "estimated_unit_cost", "company",
    )
    list_filter = ("company",)
    search_fields = ("code",)
    autocomplete_fields = ("requisition", "company")