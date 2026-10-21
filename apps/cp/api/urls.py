from rest_framework.routers import DefaultRouter

from apps.cp.api.views import (
    AddressViewSet, AttachmentViewSet, BankAccountViewSet,
    BlacklistViewSet, CategoryViewSet, ContactPersonViewSet,
    ContractViewSet, CounterpartyTypeViewSet, CounterpartyViewSet,
    InteractionViewSet, RatingViewSet,
)

router = DefaultRouter()
router.register("cp/counterparty-types", CounterpartyTypeViewSet, basename="cp-counterparty-types")
router.register("cp/categories", CategoryViewSet, basename="cp-categories")
router.register("cp/counterparties", CounterpartyViewSet, basename="cp-counterparties")
router.register("cp/contacts", ContactPersonViewSet, basename="cp-contacts")
router.register("cp/bank-accounts", BankAccountViewSet, basename="cp-bank-accounts")
router.register("cp/addresses", AddressViewSet, basename="cp-addresses")
router.register("cp/ratings", RatingViewSet, basename="cp-ratings")
router.register("cp/interactions", InteractionViewSet, basename="cp-interactions")
router.register("cp/contracts", ContractViewSet, basename="cp-contracts")
router.register("cp/attachments", AttachmentViewSet, basename="cp-attachments")
router.register("cp/blacklist", BlacklistViewSet, basename="cp-blacklist")

urlpatterns = router.urls