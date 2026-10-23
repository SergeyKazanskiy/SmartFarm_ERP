from rest_framework.routers import DefaultRouter

from apps.crm.api.views import (
    ActivityTypeViewSet, ActivityViewSet,
    CommercialOfferLineViewSet, CommercialOfferViewSet,
    ContactViewSet, ContractViewSet,
    LeadSourceViewSet, LeadStatusViewSet, LeadViewSet,
    OpportunityStageViewSet, OpportunityViewSet,
    PriceListItemViewSet, PriceListViewSet, SalesFunnelViewSet,
)

router = DefaultRouter()
router.register("crm/lead-sources", LeadSourceViewSet, basename="crm-lead-sources")
router.register("crm/lead-statuses", LeadStatusViewSet, basename="crm-lead-statuses")
router.register("crm/opportunity-stages", OpportunityStageViewSet, basename="crm-opportunity-stages")
router.register("crm/activity-types", ActivityTypeViewSet, basename="crm-activity-types")
router.register("crm/sales-funnels", SalesFunnelViewSet, basename="crm-sales-funnels")
router.register("crm/leads", LeadViewSet, basename="crm-leads")
router.register("crm/contacts", ContactViewSet, basename="crm-contacts")
router.register("crm/opportunities", OpportunityViewSet, basename="crm-opportunities")
router.register("crm/activities", ActivityViewSet, basename="crm-activities")
router.register("crm/commercial-offers", CommercialOfferViewSet, basename="crm-commercial-offers")
router.register("crm/commercial-offer-lines", CommercialOfferLineViewSet, basename="crm-commercial-offer-lines")
router.register("crm/price-lists", PriceListViewSet, basename="crm-price-lists")
router.register("crm/price-list-items", PriceListItemViewSet, basename="crm-price-list-items")
router.register("crm/contracts", ContractViewSet, basename="crm-contracts")

urlpatterns = router.urls