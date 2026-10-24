import pytest
from decimal import Decimal

from apps.procurement.models import Order, OrderHistory
from apps.procurement.services import (
    OrderLineService, OrderService,
    RequisitionLineService, RequisitionService, SupplierService,
)


@pytest.mark.django_db
def test_order_line_auto_total(company, supplier):
    order = OrderService.create(company_id=company.id, data={
        "order_number": "PO-1", "supplier_id": supplier.id,
        "order_date": "2026-06-01",
    })
    line = OrderLineService.create(company_id=company.id, data={
        "order_id": order.id, "material_id": 1,
        "quantity": 100, "unit_price": 145,
    })
    assert line.total_price == Decimal("14500.0000")

    order.refresh_from_db()
    assert order.total_amount == Decimal("14500.0000")


@pytest.mark.django_db
def test_order_status_transitions(company, supplier):
    order = OrderService.create(company_id=company.id, data={
        "order_number": "PO-1", "supplier_id": supplier.id,
        "order_date": "2026-06-01",
    })
    OrderLineService.create(company_id=company.id, data={
        "order_id": order.id, "material_id": 1,
        "quantity": 100, "unit_price": 145,
    })

    order = OrderService.send(company_id=company.id, order_id=order.id)
    assert order.status == "sent"

    order = OrderService.confirm(company_id=company.id, order_id=order.id)
    assert order.status == "confirmed"

    # OrderHistory: created + sent + confirmed = 3 записи
    assert OrderHistory.objects.filter(order=order).count() >= 3


@pytest.mark.django_db
def test_order_partial_and_full_receive(company, supplier):
    """Ключевой тест: частичная приёмка → partially_received, полная → completed."""
    order = OrderService.create(company_id=company.id, data={
        "order_number": "PO-1", "supplier_id": supplier.id,
        "order_date": "2026-06-01",
    })
    line = OrderLineService.create(company_id=company.id, data={
        "order_id": order.id, "material_id": 1,
        "quantity": 100, "unit_price": 145,
    })
    OrderService.send(company_id=company.id, order_id=order.id)
    OrderService.confirm(company_id=company.id, order_id=order.id)

    # Частичная приёмка 60
    order = OrderService.receive(
        company_id=company.id, order_id=order.id,
        order_line_id=line.id, received_quantity=60,
        delivery_date="2026-06-15",
    )
    assert order.status == "partially_received"
    line.refresh_from_db()
    assert line.received_quantity == Decimal("60")

    # Полная приёмка 40 (итого 100)
    order = OrderService.receive(
        company_id=company.id, order_id=order.id,
        order_line_id=line.id, received_quantity=40,
        delivery_date="2026-06-16",
    )
    assert order.status == "completed"
    assert order.actual_delivery_date == "2026-06-16"


@pytest.mark.django_db
def test_requisition_review(company):
    req = RequisitionService.create(company_id=company.id, data={
        "requisition_number": "REQ-1",
        "requisition_date": "2026-06-01",
    })
    req = RequisitionService.submit(company_id=company.id, requisition_id=req.id)
    assert req.status == "pending_approval"

    req = RequisitionService.review(
        company_id=company.id, requisition_id=req.id, new_status="approved",
    )
    assert req.status == "approved"


@pytest.mark.django_db
def test_supplier_save(company, counterparty):
    sup = SupplierService.save(company_id=company.id, data={
        "counterparty_id": counterparty.id,
        "rating": 8,
        "is_preferred": True,
    })
    assert sup.code.startswith("SUP-")
    assert sup.is_preferred is True