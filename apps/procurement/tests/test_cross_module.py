"""
Cross-module:
- Procurement.order.confirm → FIN AP-счёт.
- Procurement.order.receive_complete → WMS приход.
"""
import pytest
from django.core.management import call_command

from apps.finance.models import Invoice
from apps.procurement.models import Order, OrderLine
from apps.procurement.services import OrderService
from apps.wms.models import GoodsReceipt, Material, StorageLocation, Warehouse


@pytest.mark.django_db
def test_order_confirm_creates_ap_invoice(company, supplier):
    """Заказ подтверждён → FIN создаёт AP-счёт."""
    order = Order.objects.create(
        company=company, code="PO-1", order_number="PO-1",
        supplier=supplier, order_date="2026-06-01",
        status="sent", total_amount=14500,
    )
    OrderService.confirm(company_id=company.id, order_id=order.id)

    call_command("process_events", "--once")

    ap = Invoice.objects.filter(
        company=company,
        source_object_type="procurement_order",
        source_object_id=order.id,
        invoice_type="AP",
    ).first()
    assert ap is not None
    assert ap.amount == 14500
    assert ap.counterparty_id == supplier.counterparty_id


@pytest.mark.django_db
def test_order_receive_creates_wms_receipt(
    company, supplier, cp_type,
):
    """Заказ полностью получен → WMS создаёт приход."""
    from apps.wms.models import WarehouseType
    wt = WarehouseType.objects.create(company=company, code="WT-1", name="Склад")
    wh = Warehouse.objects.create(
        company=company, code="WH-1", name="Главный", warehouse_type=wt,
    )
    loc = StorageLocation.objects.create(
        company=company, code="LOC-1", warehouse=wh,
        location_code="A-01-01",
    )
    mat = Material.objects.create(
        company=company, code="MAT-1", material_code="PCB-1", name="Плата",
    )

    order = Order.objects.create(
        company=company, code="PO-1", order_number="PO-1",
        supplier=supplier, order_date="2026-06-01", status="confirmed",
    )
    line = OrderLine.objects.create(
        company=company, code="POL-1", order=order,
        material_id=mat.id, quantity=100, unit_price=145,
    )
    OrderService.receive(
        company_id=company.id, order_id=order.id,
        order_line_id=line.id, received_quantity=100,
        delivery_date="2026-06-15",
    )
    call_command("process_events", "--once")

    gr = GoodsReceipt.objects.filter(
        company=company, counterparty_id=supplier.counterparty_id,
    ).first()
    assert gr is not None
    assert gr.lines.count() == 1