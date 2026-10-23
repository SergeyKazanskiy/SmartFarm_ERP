import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.sales.models import Order


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="sm", email="sm@test.co", password="x",
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
def test_create_order(api_client, company, customer):
    r = api_client.post(
        "/api/v1/sales/orders/",
        {
            "order_number": "SO-API",
            "customer": customer.id,
            "order_date": "2026-07-01",
        },
        format="json",
    )
    assert r.status_code == 201
    assert Order.objects.filter(company=company, order_number="SO-API").exists()


@pytest.mark.django_db
def test_confirm_order_action(api_client, company, customer):
    order = Order.objects.create(
        company=company, code="SO-1", order_number="SO-1",
        customer=customer, order_date="2026-07-01", status="draft",
    )
    r = api_client.post(f"/api/v1/sales/orders/{order.id}/confirm/")
    assert r.status_code == 200
    order.refresh_from_db()
    assert order.status == "confirmed"


@pytest.mark.django_db
def test_invoice_pay_action(api_client, company, customer):
    from apps.sales.models import Invoice
    order = Order.objects.create(
        company=company, code="SO-1", order_number="SO-1",
        customer=customer, order_date="2026-07-01", total_amount=10000,
    )
    inv = Invoice.objects.create(
        company=company, code="INV-1", invoice_number="INV-1",
        order=order, invoice_date="2026-07-01",
        total_amount=10000, status="sent",
    )
    r = api_client.post(
        f"/api/v1/sales/invoices/{inv.id}/pay/",
        {"paid_amount": 10000}, format="json",
    )
    assert r.status_code == 200
    inv.refresh_from_db()
    assert inv.status == "paid"