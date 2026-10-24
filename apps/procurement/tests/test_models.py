import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.procurement.models import (
    Order, OrderLine, Requisition, RequisitionLine,
    RFQ, RFQSupplier, Supplier,
)


@pytest.mark.django_db
def test_supplier_unique_counterparty(company, counterparty):
    Supplier.objects.create(
        company=company, code="SUP-X1",
        counterparty_id=counterparty.id,
    )
    with pytest.raises(IntegrityError):
        Supplier.objects.create(
            company=company, code="SUP-X2",
            counterparty_id=counterparty.id,
        )


@pytest.mark.django_db
def test_order_protects_supplier(company, supplier):
    Order.objects.create(
        company=company, code="PO-1", order_number="PO-1",
        supplier=supplier, order_date="2026-01-01",
    )
    with pytest.raises(ProtectedError):
        supplier.delete()


@pytest.mark.django_db
def test_order_lines_cascade(company, supplier):
    order = Order.objects.create(
        company=company, code="PO-1", order_number="PO-1",
        supplier=supplier, order_date="2026-01-01",
    )
    line = OrderLine.objects.create(
        company=company, code="POL-1", order=order,
        material_id=1, quantity=10, unit_price=100,
    )
    order.delete()
    assert not OrderLine.objects.filter(pk=line.pk).exists()


@pytest.mark.django_db
def test_rfq_supplier_unique_pair(company, supplier):
    rfq = RFQ.objects.create(
        company=company, code="RFQ-1", rfq_number="RFQ-1",
        rfq_date="2026-01-01",
    )
    RFQSupplier.objects.create(
        company=company, code="RFS-1", rfq=rfq, supplier=supplier,
    )
    with pytest.raises(IntegrityError):
        RFQSupplier.objects.create(
            company=company, code="RFS-2", rfq=rfq, supplier=supplier,
        )


@pytest.mark.django_db
def test_requisition_lines_cascade(company):
    req = Requisition.objects.create(
        company=company, code="REQ-1", requisition_number="REQ-1",
        requisition_date="2026-01-01",
    )
    line = RequisitionLine.objects.create(
        company=company, code="REQL-1", requisition=req,
        material_id=1, quantity=10,
    )
    req.delete()
    assert not RequisitionLine.objects.filter(pk=line.pk).exists()