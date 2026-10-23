import pytest
from django.db import IntegrityError

from apps.crm.models import Activity, ActivityType, CommercialOffer, CommercialOfferLine


@pytest.mark.django_db
def test_lead_code_unique_per_company(company, lead_status):
    from apps.crm.models import Lead
    Lead.objects.create(company=company, code="LEAD-001", lead_status=lead_status)
    with pytest.raises(IntegrityError):
        Lead.objects.create(company=company, code="LEAD-001", lead_status=lead_status)


@pytest.mark.django_db
def test_activity_cascade_on_lead_delete(company, lead):
    at = ActivityType.objects.create(company=company, code="AT-001", name="Звонок")
    from django.utils import timezone
    activity = Activity.objects.create(
        company=company, code="ACT-001", activity_type=at,
        lead=lead, activity_date=timezone.now(), is_completed=False,
    )
    lead.delete()
    assert not Activity.objects.filter(pk=activity.pk).exists()


@pytest.mark.django_db
def test_activity_cascade_on_opportunity_delete(company, opportunity):
    at = ActivityType.objects.create(company=company, code="AT-001", name="Звонок")
    from django.utils import timezone
    activity = Activity.objects.create(
        company=company, code="ACT-001", activity_type=at,
        opportunity=opportunity, activity_date=timezone.now(),
    )
    opportunity.delete()
    assert not Activity.objects.filter(pk=activity.pk).exists()


@pytest.mark.django_db
def test_offer_line_cascade_on_offer_delete(company, opportunity):
    offer = CommercialOffer.objects.create(
        company=company, code="OFFER-001", opportunity=opportunity, status="draft",
    )
    line = CommercialOfferLine.objects.create(
        company=company, offer=offer,
        description="Товар", quantity=10, unit_price=100, line_amount=1000,
    )
    offer.delete()
    assert not CommercialOfferLine.objects.filter(pk=line.pk).exists()