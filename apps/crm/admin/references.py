"""Справочники CRM."""
from django.contrib import admin

from apps.crm.models import (
    ActivityType, LeadSource, LeadStatus, OpportunityStage, SalesFunnel,
)


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


@admin.register(LeadStatus)
class LeadStatusAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


@admin.register(OpportunityStage)
class OpportunityStageAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


@admin.register(SalesFunnel)
class SalesFunnelAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)