"""
Cross-module:
- Sales.order.produce → ProductionOrder создан (если BOM есть).
- Production.productionOrder.confirm → WMS резервирует материалы.
- Production.productionOrder.complete → WMS приход + FIN COGS.
"""
import pytest
from decimal import Decimal

from django.core.management import call_command

from apps.cp.models import Counterparty, CounterpartyType
from apps.finance.models import FinancialIndicator
from apps.production.models import (
    Bom, BomItem, ProductionOrder,
)
from apps.production.services import ProductionOrderService
from apps.sales.services import (
    CustomerService, OrderLineService, OrderService,
)
from apps.wms.models import (
    GoodsReceipt, Material, MaterialReservation,
    StorageLocation, Warehouse, WarehouseType,
)


@pytest.fixture
def wms_setup(company):
    wt = WarehouseType.objects.create(company=company, code="WT-1", name="Склад")
    wh = Warehouse.objects.create(
        company=company, code="WH-1", name="Главный", warehouse_type=wt,
    )
    loc = StorageLocation.objects.create(
        company=company, code="LOC-1", warehouse=wh,
        location_code="A-01-01",
    )
    mat_product = Material.objects.create(
        company=company, code="MAT-FIN", material_code="TV-1", name="SmartTV",
    )
    mat_component = Material.objects.create(
        company=company, code="MAT-COMP", material_code="PCB-1", name="Плата",
    )
    return {
        "warehouse": wh, "location": loc,
        "product": mat_product, "component": mat_component,
    }


@pytest.mark.django_db
def test_sales_order_produce_creates_production_order(
    company, wms_setup,
):
    """Sales.order.produce → ProductionOrder по material из BOM."""
    mat_product = wms_setup["product"]
    bom = Bom.objects.create(
        company=company, code="BOM-SALES",
        product_material_id=mat_product.id, name="SmartTV X-100",
    )

    cp_type = CounterpartyType.objects.create(
        company=company, code="CPT-S", name="Клиент",
    )
    cp = Counterparty.objects.create(
        company=company, code="CP-S", name="Клиент", counterparty_type=cp_type,
    )
    cust = CustomerService.save(company_id=company.id, data={
        "counterparty_id": cp.id,
    })
    order = OrderService.create(company_id=company.id, data={
        "order_number": "SO-PROD", "customer_id": cust.id,
        "order_date": "2026-07-01",
    })
    OrderLineService.create(company_id=company.id, data={
        "order_id": order.id, "material_id": mat_product.id,
        "quantity": 10, "unit_price": 5500,
    })
    # Триггерим событие Sales.order.produce
    from core.event_bus import EventBus
    from core.events import SalesEvents as SE
    EventBus.publish(
        SE.ORDER_PRODUCE,
        company_id=company.id,
        payload={"order_id": order.id, "production_order_id": 999},
    )
    call_command("process_events", "--once")

    prod = ProductionOrder.objects.filter(
        company=company, bom=bom,
    ).first()
    assert prod is not None
    assert prod.planned_quantity == 10


@pytest.mark.django_db
def test_production_confirm_reserves_materials(
    company, bom, routing, wms_setup,
):
    """ProductionOrder.confirm → WMS резервирует материалы по BOM."""
    # Переопределим BOM: один компонент
    bom.product_material_id = wms_setup["product"].id
    bom.save()
    BomItem.objects.create(
        company=company, code="BOMI-C1", bom=bom,
        material_id=wms_setup["component"].id,
        quantity=2, unit_cost=145,
    )

    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": routing.id,
        "planned_quantity": 100,
    })
    ProductionOrderService.confirm(
        company_id=company.id, production_order_id=order.id,
    )
    call_command("process_events", "--once")

    reservation = MaterialReservation.objects.filter(
        company=company,
        material_id=wms_setup["component"].id,
        task_object_type="production_order",
        task_object_id=order.id,
    ).first()
    assert reservation is not None
    assert reservation.quantity == Decimal("200")  # 2 × 100


@pytest.mark.django_db
def test_production_complete_creates_wms_receipt_and_fin_cogs(
    company, bom, routing, wms_setup,
):
    """ProductionOrder.complete → WMS приход + FIN COGS."""
    # BOM с product = finished, component с unit_cost
    bom.product_material_id = wms_setup["product"].id
    bom.save()
    BomItem.objects.create(
        company=company, code="BOMI-C1", bom=bom,
        material_id=wms_setup["component"].id,
        quantity=1, unit_cost=145,
    )

    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": routing.id,
        "planned_quantity": 10,
    })
    ProductionOrderService.confirm(
        company_id=company.id, production_order_id=order.id,
    )
    ProductionOrderService.complete(
        company_id=company.id, production_order_id=order.id,
    )
    call_command("process_events", "--once")

    gr = GoodsReceipt.objects.filter(
        company=company, code__startswith=f"GR-PROD-{order.id}",
    ).first()
    assert gr is not None
    assert gr.lines.first().quantity == Decimal("10")

    fi = FinancialIndicator.objects.filter(
        company=company, code=f"FI-PROD-{order.id}",
    ).first()
    assert fi is not None
    assert fi.indicator_value == Decimal("1450.0000")  # 1×145×10