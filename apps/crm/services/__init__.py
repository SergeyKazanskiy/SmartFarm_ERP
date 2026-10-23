from apps.crm.services.activities import ActivityService
from apps.crm.services.contracts import ContractService
from apps.crm.services.leads import ContactService, LeadService
from apps.crm.services.offers import CommercialOfferLineService, CommercialOfferService
from apps.crm.services.opportunities import OpportunityService
from apps.crm.services.pricelists import PriceListItemService, PriceListService
from apps.crm.services.references import (
    ActivityTypeService, LeadSourceService, LeadStatusService,
    OpportunityStageService, SalesFunnelService,
)

__all__ = [
    "LeadSourceService", "LeadStatusService", "OpportunityStageService",
    "ActivityTypeService", "SalesFunnelService",
    "LeadService", "ContactService",
    "OpportunityService",
    "ActivityService",
    "CommercialOfferService", "CommercialOfferLineService",
    "PriceListService", "PriceListItemService",
    "ContractService",
]