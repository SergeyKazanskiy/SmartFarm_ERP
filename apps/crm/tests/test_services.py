import pytest

from core.event_bus import DomainEvent
from core.events import CRMEvents as CRM

from apps.crm.models import ActivityType
from apps.crm.services import (
    ActivityService, CommercialOfferLineService, CommercialOfferService,
    LeadService, OpportunityService,
)


@pytest.mark.django_db
def test_lead_create_publishes_event(company, lead_status):
    lead = LeadService.create(
        company_id=company.id,
        data={"lead_status_id": lead_status.id, "title": "X"},
        actor_employee_id=10,
    )
    event = DomainEvent.objects.filter(
        event_type=CRM.LEAD_CREATE, company=company,
    ).latest("id")
    assert event.payload["lead_id"] == lead.id


@pytest.mark.django_db
def test_lead_update_status(company, lead, lead_status):
    LeadService.update_status(
        company_id=company.id, lead_id=lead.id,
        new_status_id=lead_status.id,
    )
    lead.refresh_from_db()
    assert lead.lead_status_id == lead_status.id
    assert DomainEvent.objects.filter(
        event_type=CRM.LEAD_UPDATE_STATUS, company=company,
    ).exists()


@pytest.mark.django_db
def test_opportunity_win(company, opportunity):
    OpportunityService.win(
        company_id=company.id, opportunity_id=opportunity.id,
    )
    opportunity.refresh_from_db()
    assert opportunity.is_won == 1
    assert DomainEvent.objects.filter(
        event_type=CRM.OPPORTUNITY_WIN, company=company,
    ).exists()


@pytest.mark.django_db
def test_opportunity_win_fails_if_closed(company, opportunity):
    opportunity.is_won = 1
    opportunity.save()
    with pytest.raises(ValueError):
        OpportunityService.win(
            company_id=company.id, opportunity_id=opportunity.id,
        )


@pytest.mark.django_db
def test_offer_flow(company, opportunity):
    offer = CommercialOfferService.create(
        company_id=company.id,
        data={"opportunity_id": opportunity.id},
    )
    CommercialOfferLineService.create(
        company_id=company.id,
        data={
            "offer_id": offer.id,
            "description": "Товар",
            "quantity": 10, "unit_price": 5000,
        },
    )
    offer = CommercialOfferService.send(
        company_id=company.id, offer_id=offer.id,
    )
    assert offer.status == "sent"
    assert offer.total_amount == 50000

    offer = CommercialOfferService.accept(
        company_id=company.id, offer_id=offer.id,
    )
    assert offer.status == "accepted"


@pytest.mark.django_db
def test_activity_complete(company, lead):
    at = ActivityType.objects.create(company=company, code="AT-001", name="Звонок")
    act = ActivityService.create(
        company_id=company.id,
        data={
            "lead_id": lead.id,
            "activity_type_id": at.id,
        },
        actor_employee_id=10,
    )
    act = ActivityService.complete(
        company_id=company.id, activity_id=act.id, result="Клиент заинтересован",
    )
    assert act.is_completed is True
    assert act.result == "Клиент заинтересован"