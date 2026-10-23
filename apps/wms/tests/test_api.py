import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.wms.models import GoodsReceipt, Inventory


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="wms", email="w@test.co", password="x",
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
def test_list_materials(api_client, material):
    r = api_client.get("/api/v1/wms/materials/")
    assert r.status_code == 200
    assert len(r.json()["results"]) >= 1


@pytest.mark.django_db
def test_post_receipt_action(api_client, company, warehouse, material, location):
    gr = GoodsReceipt.objects.create(
        company=company, code="GR-1", warehouse=warehouse,
        receipt_date="2026-06-01T10:00:00Z", status="draft",
    )
    from apps.wms.models import GoodsReceiptLine
    GoodsReceiptLine.objects.create(
        company=company, code="GRL-1", receipt=gr, material=material,
        location=location, quantity=100, unit_cost=145,
    )
    r = api_client.post(f"/api/v1/wms/goods-receipts/{gr.id}/post/")
    assert r.status_code == 200
    gr.refresh_from_db()
    assert gr.status == "posted"

    inv = Inventory.objects.filter(company=company, material=material).first()
    assert inv.quantity == 100


@pytest.mark.django_db
def test_inventory_list(api_client, inventory):
    r = api_client.get("/api/v1/wms/inventory/")
    assert r.status_code == 200