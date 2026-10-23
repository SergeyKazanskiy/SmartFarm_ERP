from apps.sales.services.customers import CustomerService
from apps.sales.services.invoices import InvoiceService
from apps.sales.services.opportunities import OpportunityService
from apps.sales.services.orders import OrderLineService, OrderService
from apps.sales.services.pricelists import PriceListLineService, PriceListService
from apps.sales.services.quotes import QuoteLineService, QuoteService
from apps.sales.services.returns import ReturnLineService, ReturnService
from apps.sales.services.shipments import ShipmentLineService, ShipmentService

__all__ = [
    "CustomerService",
    "PriceListService", "PriceListLineService",
    "OpportunityService",
    "QuoteService", "QuoteLineService",
    "OrderService", "OrderLineService",
    "ShipmentService", "ShipmentLineService",
    "ReturnService", "ReturnLineService",
    "InvoiceService",
]