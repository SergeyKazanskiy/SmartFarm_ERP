import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.procurement.models import Order


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="pm", email="pm@test.co", password="x",
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
def test_create_order(api_client, company, supplier):
    r = api_client.post(
        "/api/v1/procurement/orders/",
        {
            "order_number": "PO-API",
            "supplier": supplier.id,
            "order_date": "2026-06-01",
        },
        format="json",
    )
    assert r.status_code == 201
    assert Order.objects.filter(company=company, order_number="PO-API").exists()


@pytest.mark.django_db
def test_confirm_order_action(api_client, company, supplier):
    order = Order.objects.create(
        company=company, code="PO-1", order_number="PO-1",
        supplier=supplier, order_date="2026-06-01", status="sent",
    )
    r = api_client.post(f"/api/v1/procurement/orders/{order.id}/confirm/")
    assert r.status_code == 200
    order.refresh_from_db()
    assert order.status == "confirmed"


@pytest.mark.django_db
def test_receive_action(api_client, company, supplier):
    from apps.procurement.models import OrderLine
    order = Order.objects.create(
        company=company, code="PO-1", order_number="PO-1",
        supplier=supplier, order_date="2026-06-01", status="confirmed",
    )
    line = OrderLine.objects.create(
        company=company, code="POL-1", order=order,
        material_id=1, quantity=100, unit_price=145,
    )
    r = api_client.post(
        f"/api/v1/procurement/orders/{order.id}/receive/",
        {
            "order_line_id": line.id,
            "received_quantity": 100,
            "delivery_date": "2026-06-15",
        },
        format="json",
    )
    assert r.status_code == 200
    order.refresh_from_db()
    assert order.status == "completed"