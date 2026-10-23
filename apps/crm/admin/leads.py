"""Админка лидов."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from apps.crm.models import Lead, Activity, LeadStatus 

# Класс для отображения активностей, связанных с лидом, в виде табличного инлайна
class LeadActivityInline(admin.TabularInline):
    model = Activity  # <--- ИСПРАВЛЕНО: теперь передается класс модели, а не строка "crm.Activity"
    fk_name = "lead"
    extra = 0
    fields = ("code", "activity_type", "activity_date", "is_completed", "subject")
    readonly_fields = ("code",)
    show_change_link = True


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "title", "lead_status", "lead_source",
        "counterparty_id", "responsible_employee_id", "company",
    )
    list_filter = ("company", "lead_status", "lead_source")
    search_fields = ("code", "title", "contact_name", "contact_phone", "contact_email")
    autocomplete_fields = ("lead_source", "lead_status", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("lead_status", "lead_source")
    inlines = [LeadActivityInline]

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "title", "description"),
        }),
        (_("Источник и статус"), {
            "fields": ("lead_source", "lead_status"),
        }),
        (_("Связи"), {
            "fields": ("counterparty_id", "responsible_employee_id"),
        }),
        (_("Контакт (быстрый ввод)"), {
            "fields": ("contact_name", "contact_phone", "contact_email"),
        }),
        (_("Служебное"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["mark_qualified", "mark_rejected"]

    @admin.action(description=_("Отметить как 'Квалифицирован'"))
    def mark_qualified(self, request, queryset):
        try:
            status = LeadStatus.objects.get(name__iexact="Квалифицирован")
            queryset.update(lead_status=status)
        except LeadStatus.DoesNotExist:
            pass

    @admin.action(description=_("Отметить как 'Отказ'"))
    def mark_rejected(self, request, queryset):
        try:
            status = LeadStatus.objects.get(name__iexact="Отказ")
            queryset.update(lead_status=status)
        except LeadStatus.DoesNotExist:
            pass
