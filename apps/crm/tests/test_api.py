import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.crm.models import Opportunity


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="mgr", email="m@test.co", password="x",
    )
    u.companies.add(company)
    u.current_company = company
    u.hr_employee_id = 10
    u.save()
    return u


@pytest.fixture
def api_client(api_user):
    c = APIClient()
    c.force_authenticate(user=api_user)
    return c


@pytest.mark.django_db
def test_list_leads(api_client, lead):
    r = api_client.get("/api/v1/crm/leads/")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 1


@pytest.mark.django_db
def test_create_lead(api_client, company, lead_status):
    r = api_client.post(
        "/api/v1/crm/leads/",
        {"lead_status": lead_status.id, "title": "Из API"},
        format="json",
    )
    assert r.status_code == 201


@pytest.mark.django_db
def test_opportunity_win_action(api_client, opportunity):
    r = api_client.post(f"/api/v1/crm/opportunities/{opportunity.id}/win/")
    assert r.status_code == 200
    opportunity.refresh_from_db()
    assert opportunity.is_won == 1


@pytest.mark.django_db
def test_opportunity_lose_action(api_client, opportunity):
    r = api_client.post(
        f"/api/v1/crm/opportunities/{opportunity.id}/lose/",
        {"lost_reason": "цена"}, format="json",
    )
    assert r.status_code == 200
    opportunity.refresh_from_db()
    assert opportunity.is_won == 0
    assert opportunity.lost_reason == "цена"