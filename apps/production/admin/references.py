"""Админка мастер-данных: технологии, маршруты, центры, операции, контрольные точки."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.production.models import (
    MaterialPriceHistory, OperationDefinition, QualityPoint,
    Routing, Technology, WorkCenter,
)


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(WorkCenter)
class WorkCenterAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)
    readonly_fields = ("created_at", "updated_at")


class OperationInline(admin.TabularInline):
    model = OperationDefinition
    extra = 0
    fields = (
        "code", "name", "sequence_no", "work_center",
        "resources_json", "parameters_json",
    )


@admin.register(Routing)
class RoutingAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "technology", "company")
    list_filter = ("company", "technology")
    search_fields = ("code", "name")
    autocomplete_fields = ("technology", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("technology",)
    inlines = [OperationInline]


class QualityPointInline(admin.TabularInline):
    model = QualityPoint
    extra = 0
    fields = ("code", "name")


@admin.register(OperationDefinition)
class OperationDefinitionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "routing", "sequence_no",
        "work_center", "company",
    )
    list_filter = ("company", "routing", "work_center")
    search_fields = ("code", "name")
    autocomplete_fields = ("routing", "work_center", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("routing", "work_center")
    inlines = [QualityPointInline]


@admin.register(QualityPoint)
class QualityPointAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "operation", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("operation", "company")


@admin.register(MaterialPriceHistory)
class MaterialPriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "material_id", "unit_cost",
        "effective_date", "created_by_employee_id", "company",
    )
    list_filter = ("company", "effective_date")
    search_fields = ("code", "material_id")
    autocomplete_fields = ("company",)
    date_hierarchy = "effective_date"