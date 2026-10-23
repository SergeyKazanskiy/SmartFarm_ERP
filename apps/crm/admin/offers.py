"""Админка коммерческих предложений."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from apps.crm.models import CommercialOffer, CommercialOfferLine


class CommercialOfferLineInline(admin.TabularInline):
    model = CommercialOfferLine
    extra = 0
    fields = ("description", "price_list_item", "quantity", "unit_price", "line_amount")
    autocomplete_fields = ("price_list_item",)


@admin.register(CommercialOffer)
class CommercialOfferAdmin(admin.ModelAdmin):
    list_display = (
        "id", "code", "opportunity", "offer_date",
        "status", "total_amount", "company",
    )
    list_filter = ("company", "status")
    search_fields = ("code", "opportunity__code")
    autocomplete_fields = ("opportunity", "company")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "offer_date"
    list_select_related = ("opportunity",)
    inlines = [CommercialOfferLineInline]

    actions = ["send_offers", "accept_offers", "decline_offers"]

    @admin.action(description=_("Отметить как 'Отправлено'"))
    def send_offers(self, request, queryset):
        queryset.filter(status="draft").update(status="sent")

    @admin.action(description=_("Отметить как 'Принято'"))
    def accept_offers(self, request, queryset):
        queryset.filter(status="sent").update(status="accepted")

    @admin.action(description=_("Отметить как 'Отклонено'"))
    def decline_offers(self, request, queryset):
        queryset.filter(status="sent").update(status="declined")