import pytest
from decimal import Decimal

from core.event_bus import DomainEvent
from core.events import SalesEvents as SE

from apps.sales.services import (
    CustomerService, InvoiceService, OpportunityService,
    OrderLineService, OrderService,
    QuoteLineService, QuoteService,
    ShipmentLineService, ShipmentService,
)


@pytest.mark.django_db
def test_customer_save_publishes_event(company, counterparty):
    cust = CustomerService.save(
        company_id=company.id,
        data={
            "counterparty_id": counterparty.id,
            "category": "VIP",
            "credit_limit": 500000,
        },
    )
    assert cust.code.startswith("CUST-")
    assert DomainEvent.objects.filter(
        event_type=SE.CUSTOMER_SAVE, company=company,
    ).exists()


@pytest.mark.django_db
def test_opportunity_auto_probability(company, customer):
    opp = OpportunityService.create(
        company_id=company.id,
        data={"customer_id": customer.id, "name": "X"},
        actor_employee_id=1,
    )
    assert opp.stage == "lead"
    assert opp.probability_percent == 10

    opp = OpportunityService.update_stage(
        company_id=company.id, opportunity_id=opp.id, new_stage="proposal",
    )
    assert opp.probability_percent == 60

    opp = OpportunityService.update_stage(
        company_id=company.id, opportunity_id=opp.id, new_stage="closed_won",
    )
    assert opp.probability_percent == 100


@pytest.mark.django_db
def test_quote_line_auto_total(company, customer):
    quote = QuoteService.create(
        company_id=company.id,
        data={
            "quote_number": "Q-001",
            "customer_id": customer.id,
            "quote_date": "2026-07-01",
        },
    )
    line = QuoteLineService.create(
        company_id=company.id,
        data={
            "quote_id": quote.id,
            "material_id": 6,
            "quantity": 50,
            "unit_price": 5500,
            "discount_percent": 10,
        },
    )
    assert line.total_price == Decimal("247500.0000")

    quote.refresh_from_db()
    assert quote.total_amount == Decimal("247500.0000")


@pytest.mark.django_db
def test_order_line_auto_total(company, customer):
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-001",
            "customer_id": customer.id,
            "order_date": "2026-07-01",
        },
    )
    OrderLineService.create(
        company_id=company.id,
        data={
            "order_id": order.id,
            "material_id": 6,
            "quantity": 10,
            "unit_price": 1000,
        },
    )
    order.refresh_from_db()
    assert order.total_amount == Decimal("10000.0000")


@pytest.mark.django_db
def test_shipment_completes_order(company, customer):
    """
    Если все позиции отгружены — заказ становится completed.
    """
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-001",
            "customer_id": customer.id,
            "order_date": "2026-07-01",
        },
    )
    line = OrderLineService.create(
        company_id=company.id,
        data={
            "order_id": order.id,
            "material_id": 6,
            "quantity": 50,
            "unit_price": 5500,
        },
    )
    OrderService.confirm(company_id=company.id, order_id=order.id)

    shipment = ShipmentService.create(
        company_id=company.id,
        data={
            "shipment_number": "SH-001",
            "order_id": order.id,
            "shipment_date": "2026-08-10",
        },
    )
    ShipmentLineService.create(
        company_id=company.id,
        data={
            "shipment_id": shipment.id,
            "order_line_id": line.id,
            "quantity": 50,
        },
    )
    ShipmentService.ship(company_id=company.id, shipment_id=shipment.id)

    order.refresh_from_db()
    line.refresh_from_db()
    assert line.shipped_quantity == Decimal("50")
    assert order.status == "completed"
    assert order.actual_ship_date is not None


@pytest.mark.django_db
def test_partial_shipment(company, customer):
    """Отгрузка части позиции не завершает заказ."""
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-P",
            "customer_id": customer.id,
            "order_date": "2026-07-01",
        },
    )
    line = OrderLineService.create(
        company_id=company.id,
        data={
            "order_id": order.id,
            "material_id": 6,
            "quantity": 100,
            "unit_price": 1000,
        },
    )
    OrderService.confirm(company_id=company.id, order_id=order.id)

    shipment = ShipmentService.create(
        company_id=company.id,
        data={
            "shipment_number": "SH-P",
            "order_id": order.id,
            "shipment_date": "2026-08-10",
        },
    )
    ShipmentLineService.create(
        company_id=company.id,
        data={
            "shipment_id": shipment.id,
            "order_line_id": line.id,
            "quantity": 30,
        },
    )
    ShipmentService.ship(company_id=company.id, shipment_id=shipment.id)

    order.refresh_from_db()
    line.refresh_from_db()
    assert line.shipped_quantity == Decimal("30")
    assert order.status != "completed"


@pytest.mark.django_db
def test_invoice_pay_full(company, customer):
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-001",
            "customer_id": customer.id,
            "order_date": "2026-07-01",
        },
    )
    OrderLineService.create(
        company_id=company.id,
        data={
            "order_id": order.id,
            "material_id": 6,
            "quantity": 1,
            "unit_price": 275000,
        },
    )
    inv = InvoiceService.create(
        company_id=company.id,
        data={
            "invoice_number": "INV-001",
            "order": order,
            "invoice_date": "2026-07-01",
        },
    )
    inv = InvoiceService.pay(
        company_id=company.id, invoice_id=inv.id, paid_amount=275000,
    )
    assert inv.status == "paid"


@pytest.mark.django_db
def test_invoice_partial_pay(company, customer):
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-P2",
            "customer_id": customer.id,
            "order_date": "2026-07-01",
        },
    )
    OrderLineService.create(
        company_id=company.id,
        data={
            "order_id": order.id,
            "material_id": 6,
            "quantity": 1,
            "unit_price": 100000,
        },
    )
    inv = InvoiceService.create(
        company_id=company.id,
        data={
            "invoice_number": "INV-P",
            "order": order,
            "invoice_date": "2026-07-01",
        },
    )
    InvoiceService.send(company_id=company.id, invoice_id=inv.id)
    inv = InvoiceService.pay(
        company_id=company.id, invoice_id=inv.id, paid_amount=50000,
    )
    assert inv.status == "sent"
    assert inv.paid_amount == Decimal("50000")


@pytest.mark.django_db
def test_order_cancel_only_draft_or_confirmed(company, customer):
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-C",
            "customer_id": customer.id,
            "order_date": "2026-07-01",
        },
    )
    OrderService.confirm(company_id=company.id, order_id=order.id)
    OrderService.produce(
        company_id=company.id, order_id=order.id, production_order_id=1,
    )
    with pytest.raises(ValueError):
        OrderService.cancel(company_id=company.id, order_id=order.id)