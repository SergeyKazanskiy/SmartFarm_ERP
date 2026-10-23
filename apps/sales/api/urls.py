from rest_framework.routers import DefaultRouter

from apps.sales.api.views import (
    CustomerViewSet, InvoiceViewSet, OpportunityViewSet,
    OrderLineViewSet, OrderViewSet,
    PriceListLineViewSet, PriceListViewSet,
    QuoteLineViewSet, QuoteViewSet,
    ReturnLineViewSet, ReturnViewSet,
    ShipmentLineViewSet, ShipmentViewSet,
)

router = DefaultRouter()
router.register("sales/customers", CustomerViewSet, basename="sales-customers")
router.register("sales/price-lists", PriceListViewSet, basename="sales-price-lists")
router.register("sales/price-list-lines", PriceListLineViewSet, basename="sales-price-list-lines")
router.register("sales/opportunities", OpportunityViewSet, basename="sales-opportunities")
router.register("sales/quotes", QuoteViewSet, basename="sales-quotes")
router.register("sales/quote-lines", QuoteLineViewSet, basename="sales-quote-lines")
router.register("sales/orders", OrderViewSet, basename="sales-orders")
router.register("sales/order-lines", OrderLineViewSet, basename="sales-order-lines")
router.register("sales/shipments", ShipmentViewSet, basename="sales-shipments")
router.register("sales/shipment-lines", ShipmentLineViewSet, basename="sales-shipment-lines")
router.register("sales/returns", ReturnViewSet, basename="sales-returns")
router.register("sales/return-lines", ReturnLineViewSet, basename="sales-return-lines")
router.register("sales/invoices", InvoiceViewSet, basename="sales-invoices")

urlpatterns = router.urls