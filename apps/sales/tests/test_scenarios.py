"""
E2E по SALES_Scenarios.yml:
- SCENARIO-SALES-01: Order-to-Cash
- SCENARIO-SALES-02: Customer Return
"""
import pytest
from decimal import Decimal

from apps.sales.models import (
    Customer, Invoice, Order, OrderLine, Quote, QuoteLine,
    Return, Shipment,
)
from apps.sales.services import (
    CustomerService, InvoiceService, OpportunityService,
    OrderLineService, OrderService,
    QuoteLineService, QuoteService,
    ReturnLineService, ReturnService,
    ShipmentLineService, ShipmentService,
)


@pytest.mark.django_db
def test_scenario_sales_001_order_to_cash(company, counterparty):
    """
    Полный цикл: клиент → КП → заказ → отгрузка → счёт → оплата.
    """
    # 1. Клиент
    cust = CustomerService.save(
        company_id=company.id,
        data={
            "counterparty_id": counterparty.id,
            "category": "VIP",
            "credit_limit": 500000,
        },
    )

    # 2. Возможность → стадия proposal
    opp = OpportunityService.create(
        company_id=company.id,
        data={
            "customer_id": cust.id,
            "name": "Закупка 50 ТВ",
            "expected_value": 275000,
        },
        actor_employee_id=10,
    )
    opp = OpportunityService.update_stage(
        company_id=company.id, opportunity_id=opp.id, new_stage="proposal",
    )
    assert opp.probability_percent == 60

    # 3. КП + позиция
    quote = QuoteService.create(
        company_id=company.id,
        data={
            "quote_number": "Q-001",
            "customer_id": cust.id,
            "opportunity_id": opp.id,
            "quote_date": "2026-07-01",
        },
        actor_employee_id=10,
    )
    QuoteLineService.create(
        company_id=company.id,
        data={
            "quote_id": quote.id,
            "material_id": 6,
            "quantity": 50,
            "unit_price": 5500,
        },
    )
    quote.refresh_from_db()
    assert quote.total_amount == Decimal("275000.0000")

    # 4. Отправка и принятие КП
    quote = QuoteService.send(company_id=company.id, quote_id=quote.id)
    assert quote.status == "sent"
    quote = QuoteService.accept(company_id=company.id, quote_id=quote.id)
    assert quote.status == "accepted"

    # 5. Заказ + позиция
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-001",
            "customer_id": cust.id,
            "quote_id": quote.id,
            "order_date": "2026-07-01",
        },
        actor_employee_id=10,
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

    # 6. Подтверждение
    order = OrderService.confirm(
        company_id=company.id, order_id=order.id,
    )
    assert order.status == "confirmed"

    # 7. Отгрузка
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
    ShipmentService.deliver(company_id=company.id, shipment_id=shipment.id)

    order.refresh_from_db()
    assert order.status == "completed"

    # 8. Счёт
    inv = InvoiceService.create(
        company_id=company.id,
        data={
            "invoice_number": "INV-001",
            "order": order,
            "invoice_date": "2026-07-01",
        },
    )
    InvoiceService.send(company_id=company.id, invoice_id=inv.id)

    # 9. Оплата
    inv = InvoiceService.pay(
        company_id=company.id, invoice_id=inv.id, paid_amount=275000,
    )
    assert inv.status == "paid"


@pytest.mark.django_db
def test_scenario_sales_002_return(company, counterparty):
    """
    Цикл возврата: заказ → возврат → утверждение → приёмка.
    """
    cust = CustomerService.save(
        company_id=company.id,
        data={"counterparty_id": counterparty.id},
    )
    order = OrderService.create(
        company_id=company.id,
        data={
            "order_number": "SO-R",
            "customer_id": cust.id,
            "order_date": "2026-07-01",
        },
    )
    line = OrderLineService.create(
        company_id=company.id,
        data={
            "order_id": order.id,
            "material_id": 6,
            "quantity": 10,
            "unit_price": 5000,
        },
    )

    ret = ReturnService.create(
        company_id=company.id,
        data={
            "return_number": "RET-001",
            "order_id": order.id,
            "return_date": "2026-08-15",
            "reason": "Брак",
        },
    )
    ReturnLineService.create(
        company_id=company.id,
        data={
            "return_id": ret.id,
            "order_line_id": line.id,
            "quantity": 2,
        },
    )
    ret = ReturnService.approve(
        company_id=company.id, return_id=ret.id,
    )
    assert ret.status == "approved"

    ret = ReturnService.receive(
        company_id=company.id, return_id=ret.id,
    )
    assert ret.status == "received"