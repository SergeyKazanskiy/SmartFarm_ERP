import pytest
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from apps.cp.models import Counterparty


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    user = User.objects.create_user(
        username="manager", email="m@test.co", password="x",
    )
    user.companies.add(company)
    user.current_company = company
    user.save()
    return user


@pytest.fixture
def api_client(api_user):
    client = APIClient()
    client.force_authenticate(user=api_user)
    return client


@pytest.mark.django_db
def test_list_counterparties(api_client, counterparty):
    response = api_client.get("/api/v1/cp/counterparties/")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


@pytest.mark.django_db
def test_create_counterparty(api_client, company, cp_type):
    response = api_client.post(
        "/api/v1/cp/counterparties/",
        {
            "counterparty_type": cp_type.id,
            "name": "ООО API",
            "internal_code": "CUST-API",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Counterparty.objects.filter(
        company=company, name="ООО API",
    ).exists()


@pytest.mark.django_db
def test_block_unblock(api_client, counterparty):
    r = api_client.post(
        f"/api/v1/cp/counterparties/{counterparty.id}/block/",
        {"reason": "test"}, format="json",
    )
    assert r.status_code == 200
    counterparty.refresh_from_db()
    assert counterparty.is_blacklisted is True

    r = api_client.post(
        f"/api/v1/cp/counterparties/{counterparty.id}/unblock/",
        {"reason": "ok"}, format="json",
    )
    assert r.status_code == 200
    counterparty.refresh_from_db()
    assert counterparty.is_blacklisted is False