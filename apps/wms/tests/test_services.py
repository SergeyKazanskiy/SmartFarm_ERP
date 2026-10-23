import pytest
from decimal import Decimal

from core.event_bus import DomainEvent
from core.events import WMSEvents as WE

from apps.wms.models import Inventory, InventoryTransaction
from apps.wms.services import (
    GoodsReceiptLineService, GoodsReceiptService,
    MaterialReservationService, TransferLineService, TransferService,
    WriteOffLineService, WriteOffService,
)


@pytest.mark.django_db
def test_goods_receipt_post_moving_average(
    company, warehouse, material, location, counterparty, inventory,
):
    """
    Ключевой тест: при проведении прихода unit_cost пересчитывается
    скользящим средним.
    Старый: 1000 × 145. Новый: 500 × 160.
    Итог: (145000 + 80000) / 1500 = 150.0000
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
        "quantity": 500,
        "unit_cost": 160,
    })
    GoodsReceiptService.post(company_id=company.id, receipt_id=gr.id)

    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("1500")
    assert inventory.unit_cost == Decimal("150.0000")

    # Журнал
    assert InventoryTransaction.objects.filter(
        company=company, inventory=inventory,
        transaction_type="receipt",
        source_document_type="wms_goods_receipt",
        source_document_id=gr.id,
    ).exists()


@pytest.mark.django_db
def test_goods_receipt_cannot_post_empty(
    company, warehouse, counterparty,
):
    gr = GoodsReceiptService.create(company_id=company.id, data={
        "warehouse_id": warehouse.id,
        "receipt_date": "2026-06-01T10:00:00Z",
    })
    with pytest.raises(ValueError):
        GoodsReceiptService.post(company_id=company.id, receipt_id=gr.id)


@pytest.mark.django_db
def test_reservation_issue(company, warehouse, material, inventory):
    res = MaterialReservationService.reserve(company_id=company.id, data={
        "material_id": material.id,
        "warehouse_id": warehouse.id,
        "quantity": 100,
    })
    assert res.status == "reserved"

    res = MaterialReservationService.issue(
        company_id=company.id, reservation_id=res.id,
    )
    assert res.status == "issued"
    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("900")

    # Журнал
    assert InventoryTransaction.objects.filter(
        company=company, reservation=res, transaction_type="issue",
    ).exists()


@pytest.mark.django_db
def test_reservation_release(company, warehouse, material, inventory):
    res = MaterialReservationService.reserve(company_id=company.id, data={
        "material_id": material.id,
        "warehouse_id": warehouse.id,
        "quantity": 100,
    })
    res = MaterialReservationService.release(
        company_id=company.id, reservation_id=res.id,
    )
    assert res.status == "released"
    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("1000")  # без изменений


@pytest.mark.django_db
def test_reservation_insufficient(company, warehouse, material, inventory):
    res = MaterialReservationService.reserve(company_id=company.id, data={
        "material_id": material.id,
        "warehouse_id": warehouse.id,
        "quantity": 99999,
    })
    with pytest.raises(ValueError):
        MaterialReservationService.issue(
            company_id=company.id, reservation_id=res.id,
        )


@pytest.mark.django_db
def test_transfer_post(company, warehouse, warehouse2, material, inventory):
    # На складе-получателе должна быть ячейка
    from apps.wms.models import StorageLocation
    StorageLocation.objects.create(
        company=company, code="LOC-W2", warehouse=warehouse2,
        location_code="C-01-01", location_type="стеллажное",
    )
    tr = TransferService.create(company_id=company.id, data={
        "from_warehouse_id": warehouse.id,
        "to_warehouse_id": warehouse2.id,
        "transfer_date": "2026-06-15T10:00:00Z",
    })
    TransferLineService.create(company_id=company.id, data={
        "transfer_id": tr.id, "material_id": material.id, "quantity": 200,
    })
    TransferService.post(company_id=company.id, transfer_id=tr.id)

    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("800")

    # На складе-получателе появился остаток
    dst = Inventory.objects.filter(
        company=company, material=material,
        location__warehouse=warehouse2,
    ).first()
    assert dst is not None
    assert dst.quantity == Decimal("200")


@pytest.mark.django_db
def test_writeoff_post(company, warehouse, material, inventory):
    wo = WriteOffService.create(company_id=company.id, data={
        "warehouse_id": warehouse.id,
        "writeoff_date": "2026-06-15T10:00:00Z",
        "reason": "Брак",
    })
    WriteOffLineService.create(company_id=company.id, data={
        "writeoff_id": wo.id, "material_id": material.id, "quantity": 50,
    })
    WriteOffService.post(company_id=company.id, writeoff_id=wo.id)

    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("950")
    assert InventoryTransaction.objects.filter(
        company=company, inventory=inventory,
        transaction_type="writeoff",
        source_document_type="wms_writeoff",
    ).exists()


@pytest.mark.django_db
def test_snapshot_approve(company, warehouse, material, inventory):
    """Инвентаризация: пересчёт 990 (недостача 10) → approve."""
    from apps.wms.services import (
        InventorySnapshotService, InventorySnapshotItemService,
    )
    snap = InventorySnapshotService.create(company_id=company.id, data={
        "warehouse_id": warehouse.id,
    })
    item = snap.items.first()
    assert item.quantity == Decimal("1000")

    InventorySnapshotItemService.record_count(
        company_id=company.id, snapshot_item_id=item.id,
        counted_quantity=990,
    )
    InventorySnapshotService.finish_counting(
        company_id=company.id, snapshot_id=snap.id,
    )
    InventorySnapshotService.approve(
        company_id=company.id, snapshot_id=snap.id,
    )

    inventory.refresh_from_db()
    assert inventory.quantity == Decimal("990")
    # Должна быть запись writeoff на -10
    assert InventoryTransaction.objects.filter(
        company=company, inventory=inventory,
        transaction_type="writeoff",
        source_document_type="wms_inventory_snapshot",
    ).exists()