import pytest
from django.db import IntegrityError

from apps.sales.models import (
    Customer, Invoice, Order, OrderLine, Quote, QuoteLine,
)


@pytest.mark.django_db
def test_customer_unique_counterparty(company, counterparty):
    Customer.objects.create(
        company=company, code="CUST-1",
        counterparty_id=counterparty.id,
    )
    with pytest.raises(IntegrityError):
        Customer.objects.create(
            company=company, code="CUST-2",
            counterparty_id=counterparty.id,
        )


@pytest.mark.django_db
def test_order_protected_from_customer_delete(company, customer):
    from django.db.models import ProtectedError
    Order.objects.create(
        company=company, code="SO-1", order_number="SO-1",
        customer=customer, order_date="2026-07-01",
    )
    with pytest.raises(ProtectedError):
        customer.delete()


@pytest.mark.django_db
def test_invoice_protected_from_order_delete(company, customer):
    from django.db.models import ProtectedError
    order = Order.objects.create(
        company=company, code="SO-1", order_number="SO-1",
        customer=customer, order_date="2026-07-01",
    )
    Invoice.objects.create(
        company=company, code="INV-1", invoice_number="INV-1",
        order=order, invoice_date="2026-07-01",
    )
    with pytest.raises(ProtectedError):
        order.delete()


@pytest.mark.django_db
def test_quote_lines_cascade_on_quote_delete(company, customer):
    q = Quote.objects.create(
        company=company, code="Q-1", quote_number="Q-1",
        customer=customer, quote_date="2026-07-01",
    )
    line = QuoteLine.objects.create(
        company=company, code="QL-1", quote=q,
        material_id=6, quantity=10, unit_price=5000,
    )
    q.delete()
    assert not QuoteLine.objects.filter(pk=line.pk).exists()


@pytest.mark.django_db
def test_order_lines_cascade_on_order_delete(company, customer):
    order = Order.objects.create(
        company=company, code="SO-1", order_number="SO-1",
        customer=customer, order_date="2026-07-01",
    )
    line = OrderLine.objects.create(
        company=company, code="SOL-1", order=order,
        material_id=6, quantity=10, unit_price=5000,
    )
    order.delete()
    assert not OrderLine.objects.filter(pk=line.pk).exists()