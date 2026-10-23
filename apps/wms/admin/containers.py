"""Админка тары."""
from django.contrib import admin

from apps.wms.models import Container, ContainerItem, ContainerType


@admin.register(ContainerType)
class ContainerTypeAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "company")
    list_filter = ("company",)
    search_fields = ("code", "name")
    autocomplete_fields = ("company",)


class ContainerItemInline(admin.TabularInline):
    model = ContainerItem
    extra = 0
    fields = ("code", "inventory")
    autocomplete_fields = ("inventory",)


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "container_code", "container_type", "company")
    list_filter = ("company", "container_type")
    search_fields = ("code", "container_code")
    autocomplete_fields = ("container_type", "company")
    inlines = [ContainerItemInline]


@admin.register(ContainerItem)
class ContainerItemAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "container", "inventory", "company")
    list_filter = ("company",)
    autocomplete_fields = ("container", "inventory", "company")