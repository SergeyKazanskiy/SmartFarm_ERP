"""
Cross-module: Sales.shipment.create → списание WMS.
"""
import pytest
from decimal import Decimal

from django.core.management import call_command

from apps.cp.models import CounterpartyType
from apps.sales.services import (
    CustomerService, OrderLineService, OrderService,
    ShipmentLineService, ShipmentService,
)
from apps.wms.models import Inventory


@pytest.mark.django_db
def test_sales_shipment_decreases_inventory(
    company, material, inventory, counterparty,
):
    """
    Отгрузка Sales по material_id=material.id → уменьшает Inventory.
    """
    cust = CustomerService.save(company_id=company.id, data={
        "counterparty_id": counterparty.id,
    })
    order = OrderService.create(company_id=company.id, data={
        "order_number": "SO-WMS-1", "customer_id": cust.id,
        "order_date": "2026-07-01",
    })
    line = OrderLineService.create(company_id=company.id, data={
        "order_id": order.id, "material_id": material.id,
        "quantity": 50, "unit_price": 5500,
    })
    OrderService.confirm(company_id=company.id, order_id=order.id)

    sh = ShipmentService.create(company_id=company.id, data={
        "shipment_number": "SH-WMS-1", "order_id": order.id,
        "shipment_date": "2026-08-10",
    })
    ShipmentLineService.create(company_id=company.id, data={
        "shipment_id": sh.id, "order_line_id": line.id, "quantity": 50,
    })

    call_command("process_events", "--once")

    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("950")  # 1000 - 50