"""
Cross-module: CP.blacklist.add → отмена заказов Sales.
"""
import pytest
from django.core.management import call_command

from apps.cp.services import BlacklistService
from apps.sales.models import Order


@pytest.mark.django_db
def test_blacklist_cancels_orders(company, counterparty, customer):
    order = Order.objects.create(
        company=company, code="SO-1", order_number="SO-1",
        customer=customer, order_date="2026-07-01", status="confirmed",
    )
    BlacklistService.add(
        company_id=company.id,
        counterparty_id=counterparty.id,
        reason="test",
    )
    call_command("process_events", "--once")

    order.refresh_from_db()
    assert order.status == "cancelled"