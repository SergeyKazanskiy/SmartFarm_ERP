import pytest

from apps.companies.models import Company
from apps.cp.models import Counterparty, CounterpartyType
from apps.wms.models import (
    Inventory, Material, MaterialGroup, StorageLocation,
    Warehouse, WarehouseType,
)


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def warehouse_type(company):
    return WarehouseType.objects.create(
        company=company, code="WT-001", name="Центральный склад",
    )


@pytest.fixture
def warehouse(company, warehouse_type):
    return Warehouse.objects.create(
        company=company, code="WH-001", name="Центральный",
        warehouse_type=warehouse_type,
    )


@pytest.fixture
def warehouse2(company, warehouse_type):
    return Warehouse.objects.create(
        company=company, code="WH-002", name="Готовая продукция",
        warehouse_type=warehouse_type,
    )


@pytest.fixture
def location(company, warehouse):
    return StorageLocation.objects.create(
        company=company, code="LOC-001", warehouse=warehouse,
        location_code="A-01-01", location_type="паллетное",
    )


@pytest.fixture
def location2(company, warehouse):
    return StorageLocation.objects.create(
        company=company, code="LOC-002", warehouse=warehouse,
        location_code="A-01-02", location_type="паллетное",
    )


@pytest.fixture
def material_group(company):
    return MaterialGroup.objects.create(
        company=company, code="MG-001", name="Электронные компоненты",
    )


@pytest.fixture
def material(company, material_group):
    return Material.objects.create(
        company=company, code="MAT-001", material_code="PCB-001",
        name="Печатная плата", material_group=material_group,
        min_stock_level=500,
    )


@pytest.fixture
def inventory(company, material, location):
    return Inventory.objects.create(
        company=company, code="INV-001", material=material,
        location=location, quantity=1000, unit_cost=145,
    )


@pytest.fixture
def cp_type(company):
    return CounterpartyType.objects.create(
        company=company, code="CPT-W", name="Поставщик",
    )


@pytest.fixture
def counterparty(company, cp_type):
    return Counterparty.objects.create(
        company=company, code="CP-001", name="Поставщик X",
        counterparty_type=cp_type,
    )