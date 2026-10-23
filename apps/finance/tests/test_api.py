import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.finance.models import Invoice


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="acc", email="acc@test.co", password="x",
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
def test_create_invoice(api_client, counterparty):
    r = api_client.post(
        "/api/v1/finance/invoices/",
        {
            "invoice_type": "AP", "counterparty_id": counterparty.id,
            "invoice_date": "2026-06-01", "amount": 1000,
        },
        format="json",
    )
    assert r.status_code == 201
    assert Invoice.objects.filter(
        counterparty_id=counterparty.id, invoice_type="AP",
    ).exists()


@pytest.mark.django_db
def test_issue_invoice_action(api_client, ap_invoice):
    r = api_client.post(
        f"/api/v1/finance/invoices/{ap_invoice.id}/issue/",
    )
    assert r.status_code == 200
    ap_invoice.refresh_from_db()
    assert ap_invoice.status == "issued"


@pytest.mark.django_db
def test_payment_complete_action(
    api_client, company, accounts, ap_invoice, bank_account,
):
    from apps.finance.models import Payment
    payment = Payment.objects.create(
        company=company, code="PAY-1", invoice=ap_invoice,
        bank_account=bank_account, payment_status="planned",
        payment_date="2026-06-15T10:00:00Z", amount=100000,
    )
    r = api_client.post(
        f"/api/v1/finance/payments/{payment.id}/complete/",
    )
    assert r.status_code == 200
    payment.refresh_from_db()
    assert payment.payment_status == "completed"
    ap_invoice.refresh_from_db()
    assert ap_invoice.status == "paid"