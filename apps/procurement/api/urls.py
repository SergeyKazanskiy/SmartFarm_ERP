from rest_framework.routers import DefaultRouter

from apps.procurement.api.views import (
    DeliveryViewSet, OrderHistoryViewSet, OrderLineViewSet, OrderViewSet,
    RequisitionLineViewSet, RequisitionViewSet,
    RFQSupplierViewSet, RFQViewSet, SupplierQuoteViewSet, SupplierViewSet,
)

router = DefaultRouter()
router.register("procurement/suppliers", SupplierViewSet, basename="proc-suppliers")
router.register("procurement/requisitions", RequisitionViewSet, basename="proc-requisitions")
router.register("procurement/requisition-lines", RequisitionLineViewSet, basename="proc-requisition-lines")
router.register("procurement/rfqs", RFQViewSet, basename="proc-rfqs")
router.register("procurement/rfq-suppliers", RFQSupplierViewSet, basename="proc-rfq-suppliers")
router.register("procurement/supplier-quotes", SupplierQuoteViewSet, basename="proc-supplier-quotes")
router.register("procurement/orders", OrderViewSet, basename="proc-orders")
router.register("procurement/order-lines", OrderLineViewSet, basename="proc-order-lines")
router.register("procurement/order-history", OrderHistoryViewSet, basename="proc-order-history")
router.register("procurement/deliveries", DeliveryViewSet, basename="proc-deliveries")

urlpatterns = router.urls