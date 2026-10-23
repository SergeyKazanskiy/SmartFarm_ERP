"""
E2E по WMS_Scenarios.yml:
- SCENARIO-WMS-01: Inbound (приёмка)
- SCENARIO-WMS-02: Outbound (отгрузка)
- SCENARIO-WMS-03: Cycle Counting (инвентаризация)
"""
import pytest
from decimal import Decimal

from apps.wms.models import (
    Inventory, InventoryTransaction, MaterialReservation,
)
from apps.wms.services import (
    GoodsReceiptLineService, GoodsReceiptService,
    InventorySnapshotItemService, InventorySnapshotService,
    MaterialReservationService,
)


@pytest.mark.django_db
def test_scenario_wms_001_inbound(
    company, warehouse, material, location, counterparty,
):
    """
    Inbound: приход → скользящее среднее → журнал.
    """
    gr = GoodsReceiptService.create(company_id=company.id, data={
        "warehouse_id": warehouse.id,
        "counterparty_id": counterparty.id,
        "receipt_date": "2026-06-01T10:00:00Z",
    })
    GoodsReceiptLineService.create(company_id=company.id, data={
        "receipt_id": gr.id,
        "material_id": material.id,
        "location_id": location.id,
        "quantity": 1000,
        "unit_cost": 145,
    })
    GoodsReceiptService.post(company_id=company.id, receipt_id=gr.id)

    inv = Inventory.objects.get(company=company, material=material)
    assert inv.quantity == 1000
    assert inv.unit_cost == Decimal("145.0000")

    assert InventoryTransaction.objects.filter(
        company=company, inventory=inv, transaction_type="receipt",
    ).count() == 1


@pytest.mark.django_db
def test_scenario_wms_002_outbound(
    company, warehouse, material, inventory,
):
    """
    Outbound: резервирование → выдача.
    """
    res = MaterialReservationService.reserve(company_id=company.id, data={
        "material_id": material.id,
        "warehouse_id": warehouse.id,
        "quantity": 200,
    })
    res = MaterialReservationService.issue(
        company_id=company.id, reservation_id=res.id,
    )

    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("800")

    assert InventoryTransaction.objects.filter(
        company=company, reservation=res, transaction_type="issue",
    ).count() == 1


@pytest.mark.django_db
def test_scenario_wms_003_cycle_count(
    company, warehouse, material, inventory,
):
    """
    Инвентаризация: снимок → пересчёт 980 (недостача 20) → approve.
    """
    snap = InventorySnapshotService.create(company_id=company.id, data={
        "warehouse_id": warehouse.id,
    })
    item = snap.items.first()
    InventorySnapshotItemService.record_count(
        company_id=company.id, snapshot_item_id=item.id,
        counted_quantity=980,
    )
    InventorySnapshotService.finish_counting(
        company_id=company.id, snapshot_id=snap.id,
    )
    InventorySnapshotService.approve(
        company_id=company.id, snapshot_id=snap.id,
    )

    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("980")

    writeoff = InventoryTransaction.objects.filter(
        company=company, inventory=inventory,
        transaction_type="writeoff",
        source_document_type="wms_inventory_snapshot",
    ).first()
    assert writeoff is not None
    assert writeoff.quantity == Decimal("-20")