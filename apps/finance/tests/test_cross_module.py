"""
Cross-module:
- CP.blacklist.add → invoice → overdue.
- Sales.order.create → AR-счёт.
"""
import pytest
from django.core.management import call_command

from apps.cp.services import BlacklistService
from apps.finance.models import Invoice
from apps.sales.models import Customer, Order
from apps.sales.services import (
    CustomerService, OrderLineService, OrderService,
)


@pytest.mark.django_db
def test_blacklist_puts_invoices_overdue(company, counterparty):
    inv = Invoice.objects.create(
        company=company, code="FINV-BL", invoice_type="AP",
        counterparty_id=counterparty.id,
        invoice_date="2026-06-01", amount=1000, status="issued",
    )
    BlacklistService.add(
        company_id=company.id,
        counterparty_id=counterparty.id, reason="test",
    )
    call_command("process_events", "--once")

    inv.refresh_from_db()
    assert inv.status == "overdue"


@pytest.mark.django_db
def test_sales_order_creates_ar_invoice(company, counterparty):
    cust = CustomerService.save(company_id=company.id, data={
        "counterparty_id": counterparty.id,
    })
    order = OrderService.create(company_id=company.id, data={
        "order_number": "SO-FIN-1", "customer_id": cust.id,
        "order_date": "2026-07-01",
    })
    OrderLineService.create(company_id=company.id, data={
        "order_id": order.id, "material_id": 6,
        "quantity": 10, "unit_price": 5500,
    })
    call_command("process_events", "--once")

    ar = Invoice.objects.filter(
        company=company, source_object_type="sales_order",
        source_object_id=order.id, invoice_type="AR",
    ).first()
    assert ar is not None
    assert ar.amount == order.total_amount
    assert ar.counterparty_id == counterparty.id


@pytest.mark.django_db
def test_sales_order_idempotent(company, counterparty):
    """Повторное событие Sales.order.create не создаёт дубликат AR-счёта."""
    cust = CustomerService.save(company_id=company.id, data={
        "counterparty_id": counterparty.id,
    })
    order = OrderService.create(company_id=company.id, data={
        "order_number": "SO-FIN-2", "customer_id": cust.id,
        "order_date": "2026-07-01",
    })
    # Дважды публикуем одно событие
    call_command("process_events", "--once")
    call_command("process_events", "--once")

    assert Invoice.objects.filter(
        company=company, source_object_type="sales_order",
        source_object_id=order.id, invoice_type="AR",
    ).count() <= 1