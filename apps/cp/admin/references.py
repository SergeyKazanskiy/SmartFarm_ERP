"""Справочники: типы контрагентов и категории."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.cp.models import Category, CounterpartyType


@admin.register(CounterpartyType)
class CounterpartyTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "is_active", "company", "created_at")
    list_filter = ("company", "is_active")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("company",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "parent", "is_active", "company")
    list_filter = ("company", "is_active", "parent")
    search_fields = ("code", "name")
    autocomplete_fields = ("parent", "company")
    readonly_fields = ("created_at", "updated_at")