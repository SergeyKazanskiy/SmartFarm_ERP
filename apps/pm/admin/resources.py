"""Админка ресурсных потребностей."""
from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.pm.models import ResourceNeed


@admin.register(ResourceNeed)
class ResourceNeedAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "task", "resource_type", "quantity",
        "hours_per_day", "days_required", "sent_to_aps", "company",
    )
    list_filter = ("company", "resource_type", "sent_to_aps")
    search_fields = ("code", "task__name")
    autocomplete_fields = ("task", "company")
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("task",)

    actions = ["send_to_aps"]

    @admin.action(description=_("Отметить как отправленные в APS"))
    def send_to_aps(self, request, queryset):
        queryset.filter(sent_to_aps=False).update(
            sent_to_aps=True, sent_to_aps_at=timezone.now(),
        )