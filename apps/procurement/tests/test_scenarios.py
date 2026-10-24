"""
E2E по PROCUREMENT_Scenarios.yml:
- SCENARIO-PROC-01: полный цикл закупки (заявка → RFQ → PO → приёмка)
- SCENARIO-PROC-03: корректировка/отмена заказа
"""
import pytest
from decimal import Decimal

from apps.procurement.models import Order, OrderHistory
from apps.procurement.services import (
    OrderLineService, OrderService,
    RequisitionLineService, RequisitionService,
    RFQService, RFQSupplierService,
    SupplierQuoteService, SupplierService,
)


@pytest.mark.django_db
def test_scenario_proc_001_full_procurement(company, supplier):
    """
    Полный цикл: заявка → согласование → RFQ → предложения → PO → приёмка.
    """
    # 1. Заявка
    req = RequisitionService.create(company_id=company.id, data={
        "requisition_number": "REQ-2026-001",
        "source_type": "wms_deficit",
        "source_id": 1,
        "requisition_date": "2026-06-01",
        "required_date": "2026-06-15",
    })
    RequisitionLineService.create(company_id=company.id, data={
        "requisition_id": req.id, "material_id": 1,
        "quantity": 1000, "estimated_unit_cost": 145,
    })

    # 2. Согласование
    req = RequisitionService.submit(company_id=company.id, requisition_id=req.id)
    req = RequisitionService.review(
        company_id=company.id, requisition_id=req.id, new_status="approved",
    )
    assert req.status == "approved"

    # 3. RFQ
    rfq = RFQService.create(company_id=company.id, data={
        "rfq_number": "RFQ-2026-001",
        "requisition_id": req.id,
        "rfq_date": "2026-06-01",
        "response_deadline": "2026-06-07",
    })
    rfs = RFQSupplierService.add(company_id=company.id, data={
        "rfq_id": rfq.id, "supplier_id": supplier.id,
    })
    SupplierQuoteService.create(company_id=company.id, data={
        "rfq_supplier_id": rfs.id, "material_id": 1,
        "unit_price": 145, "quantity": 1000, "delivery_days": 5,
    })
    rfq = RFQService.send(company_id=company.id, rfq_id=rfq.id)
    rfq = RFQService.mark_responded(company_id=company.id, rfq_id=rfq.id)
    rfq = RFQService.close(company_id=company.id, rfq_id=rfq.id)
    assert rfq.status == "closed"

    # 4. PO
    order = OrderService.create(company_id=company.id, data={
        "order_number": "PO-2026-001",
        "supplier_id": supplier.id,
        "requisition_id": req.id,
        "rfq_id": rfq.id,
        "order_date": "2026-06-08",
        "expected_delivery_date": "2026-06-15",
    })
    line = OrderLineService.create(company_id=company.id, data={
        "order_id": order.id, "material_id": 1,
        "quantity": 1000, "unit_price": 145,
    })
    order.refresh_from_db()
    assert order.total_amount == Decimal("145000.0000")

    # 5. Отправка → подтверждение
    order = OrderService.send(company_id=company.id, order_id=order.id)
    order = OrderService.confirm(company_id=company.id, order_id=order.id)
    assert order.status == "confirmed"

    # 6. Приёмка
    order = OrderService.receive(
        company_id=company.id, order_id=order.id,
        order_line_id=line.id, received_quantity=1000,
        delivery_date="2026-06-14",
    )
    assert order.status == "completed"
    assert order.actual_delivery_date == "2026-06-14"

    # История
    assert OrderHistory.objects.filter(order=order).count() >= 4


@pytest.mark.django_db
def test_scenario_proc_003_cancel_order(company, supplier):
    """Отмена PO → OrderHistory фиксирует переход."""
    order = OrderService.create(company_id=company.id, data={
        "order_number": "PO-CANCEL",
        "supplier_id": supplier.id,
        "order_date": "2026-06-08",
    })
    OrderService.send(company_id=company.id, order_id=order.id)

    order = OrderService.cancel(company_id=company.id, order_id=order.id)
    assert order.status == "cancelled"

    # История содержит cancelled
    cancelled_records = OrderHistory.objects.filter(
        order=order, status_to="cancelled",
    )
    assert cancelled_records.exists()