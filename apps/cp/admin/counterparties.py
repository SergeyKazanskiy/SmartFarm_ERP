"""Основная карточка контрагента с inline-блоками."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.cp.models import (
    Address, BankAccount, ContactPerson, Counterparty,
)


class ContactPersonInline(admin.TabularInline):
    model = ContactPerson
    extra = 0
    fields = (
        "code", "last_name", "first_name", "middle_name",
        "position", "department", "phone", "mobile_phone",
        "email", "is_primary", "is_active",
    )
    readonly_fields = ("created_at", "updated_at")


class BankAccountInline(admin.TabularInline):
    model = BankAccount
    extra = 0
    fields = (
        "code", "bank_name", "bank_code", "account_number",
        "currency_id", "is_primary", "is_active",
    )


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    fields = (
        "code", "address_type", "address_line1", "address_line2",
        "city", "region", "postal_code", "country_id",
        "is_primary", "is_active",
    )


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "name", "counterparty_type", "status",
        "is_blacklisted", "responsible_employee_id", "company",
    )
    list_filter = (
        "company", "status", "is_blacklisted", "counterparty_type", "category",
    )
    search_fields = ("code", "internal_code", "name", "tax_id", "phone", "email")
    autocomplete_fields = (
        "counterparty_type", "category", "company",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    list_select_related = ("counterparty_type", "category", "company")
    inlines = [ContactPersonInline, BankAccountInline, AddressInline]

    fieldsets = (
        (_("Идентификация"), {
            "fields": ("company", "code", "internal_code", "counterparty_type", "category"),
        }),
        (_("Реквизиты"), {
            "fields": (
                "name", "short_name",
                "tax_id", "tax_registration_id", "vat_registration",
                "industry",
            ),
        }),
        (_("Адреса и контакты (краткие)"), {
            "fields": ("legal_address", "actual_address", "phone", "email", "website"),
        }),
        (_("Финансы и условия"), {
            "fields": (
                "credit_limit", "payment_terms", "delivery_terms",
            ),
        }),
        (_("Статус и ответственные"), {
            "fields": (
                "status", "is_blacklisted",
                "responsible_employee_id", "created_by_employee_id",
            ),
        }),
        (_("Служебное"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["mark_active", "mark_inactive", "mark_blocked"]

    @admin.action(description=_("Установить статус 'Активен'"))
    def mark_active(self, request, queryset):
        queryset.update(status="active", is_blacklisted=False)

    @admin.action(description=_("Установить статус 'Неактивен'"))
    def mark_inactive(self, request, queryset):
        queryset.update(status="inactive")

    @admin.action(description=_("Установить статус 'Заблокирован'"))
    def mark_blocked(self, request, queryset):
        queryset.update(status="blocked")