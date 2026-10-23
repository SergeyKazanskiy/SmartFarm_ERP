import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.wms.models import (
    GoodsReceipt, GoodsReceiptLine, Inventory, Material,
    StorageLocation,
)


@pytest.mark.django_db
def test_material_code_unique(company, material_group):
    Material.objects.create(
        company=company, code="M1", material_code="PCB-X", name="A",
        material_group=material_group,
    )
    with pytest.raises(IntegrityError):
        Material.objects.create(
            company=company, code="M2", material_code="PCB-X", name="B",
            material_group=material_group,
        )


@pytest.mark.django_db
def test_protect_material_with_inventory(inventory, material):
    """Нельзя удалить материал, у которого есть остатки."""
    with pytest.raises(ProtectedError):
        material.delete()


@pytest.mark.django_db
def test_protect_location_with_inventory(inventory, location):
    with pytest.raises(ProtectedError):
        location.delete()


@pytest.mark.django_db
def test_receipt_lines_cascade(company, warehouse, material, location, counterparty):
    gr = GoodsReceipt.objects.create(
        company=company, code="GR-1", warehouse=warehouse,
        counterparty_id=counterparty.id, receipt_date="2026-01-01T00:00:00Z",
    )
    line = GoodsReceiptLine.objects.create(
        company=company, code="GRL-1", receipt=gr, material=material,
        location=location, quantity=100, unit_cost=145,
    )
    gr.delete()
    assert not GoodsReceiptLine.objects.filter(pk=line.pk).exists()


@pytest.mark.django_db
def test_inventory_unique_material_location(company, material, location):
    """Unique constraint на (company, code) — отдельный Inventory."""
    Inventory.objects.create(
        company=company, code="INV-U1", material=material,
        location=location, quantity=10,
    )
    # Другой code — можно
    Inventory.objects.create(
        company=company, code="INV-U2", material=material,
        location=location, quantity=20,
    )
    # Тот же code — нельзя
    with pytest.raises(IntegrityError):
        Inventory.objects.create(
            company=company, code="INV-U1", material=material,
            location=location, quantity=30,
        )