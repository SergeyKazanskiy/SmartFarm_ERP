"""
E2E по Production_Scenarios.yml:
- SCENARIO-PROD-01: полный производственный цикл
- SCENARIO-PROD-02: брак в производстве
"""
import pytest
from decimal import Decimal

from apps.production.models import (
    OperationExecution, ProductionOrder, WorkOrder,
)
from apps.production.services import (
    BomItemService, BomService, OperationExecutionService,
    OperationService, ProductionOrderService, QualityPointService,
    RoutingService, TechnologyService, WorkCenterService,
    WorkOrderService,
)


@pytest.mark.django_db
def test_scenario_prod_001_full_production_cycle(company):
    """
    Создание BOM → заказ → наряд → операция → качество → завершение.
    """
    # 1. Мастер-данные
    tech = TechnologyService.create(company_id=company.id, data={
        "name": "Сборка SmartTV",
    })
    wc = WorkCenterService.create(company_id=company.id, data={
        "name": "Участок сборки",
    })
    rout = RoutingService.create(company_id=company.id, data={
        "technology_id": tech.id, "name": "Маршрут сборки",
    })
    op = OperationService.create(company_id=company.id, data={
        "routing_id": rout.id, "name": "Сборка корпуса",
        "sequence_no": 1, "work_center_id": wc.id,
        "resources_json": [{"resource_type": "employee", "quantity": 2}],
        "parameters_json": [{"name": "temperature", "target_value": 22, "tolerance": 2}],
    })
    qp = QualityPointService.create(company_id=company.id, data={
        "operation_id": op.id, "name": "Проверка зазоров",
    })

    # 2. BOM
    bom = BomService.create(company_id=company.id, data={
        "product_material_id": 6, "name": "SmartTV X-100",
    })
    BomItemService.create(company_id=company.id, data={
        "bom_id": bom.id, "material_id": 1, "quantity": 1, "unit_cost": 145,
    })

    # 3. Заказ
    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": rout.id,
        "planned_quantity": 100,
        "planned_start_date": "2026-06-20",
        "planned_end_date": "2026-07-05",
    })
    order = ProductionOrderService.confirm(
        company_id=company.id, production_order_id=order.id,
    )

    # 4. Наряд
    wo = WorkOrderService.create(company_id=company.id, data={
        "production_order_id": order.id,
    })
    wo = WorkOrderService.start(company_id=company.id, work_order_id=wo.id)
    order.refresh_from_db()
    assert order.status == "in_progress"

    # 5. Выполнение операции
    ex = OperationExecutionService.start(company_id=company.id, data={
        "work_order_id": wo.id, "operation_id": op.id,
        "work_center_id": wc.id,
    })
    ex = OperationExecutionService.record_measurements(
        company_id=company.id, execution_id=ex.id,
        measurements_json=[{"parameter_name": "temperature", "measured_value": 21.5}],
    )
    ex = OperationExecutionService.record_quality(
        company_id=company.id, execution_id=ex.id,
        quality_results_json=[
            {"quality_point_id": qp.id, "is_passed": True, "comment": "OK"},
        ],
    )
    assert ex.status == "in_progress"

    ex = OperationExecutionService.complete(
        company_id=company.id, execution_id=ex.id,
    )
    assert ex.status == "completed"

    # 6. Завершение наряда и заказа
    wo = WorkOrderService.complete(company_id=company.id, work_order_id=wo.id)
    assert wo.status == "completed"

    order = ProductionOrderService.complete(
        company_id=company.id, production_order_id=order.id,
    )
    assert order.status == "completed"


@pytest.mark.django_db
def test_scenario_prod_002_scrap(company):
    """
    Брак: плохое качество → rework; после ручного возврата в работу → complete.
    """
    tech = TechnologyService.create(company_id=company.id, data={
        "name": "Сборка",
    })
    wc = WorkCenterService.create(company_id=company.id, data={"name": "Участок 1"})
    rout = RoutingService.create(company_id=company.id, data={
        "technology_id": tech.id, "name": "Маршрут",
    })
    op = OperationService.create(company_id=company.id, data={
        "routing_id": rout.id, "name": "Сборка",
        "sequence_no": 1, "work_center_id": wc.id,
    })
    qp = QualityPointService.create(company_id=company.id, data={
        "operation_id": op.id, "name": "Контроль зазоров",
    })

    bom = BomService.create(company_id=company.id, data={
        "product_material_id": 6, "name": "X-100",
    })

    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": rout.id, "planned_quantity": 5,
    })
    ProductionOrderService.confirm(
        company_id=company.id, production_order_id=order.id,
    )
    wo = WorkOrderService.create(company_id=company.id, data={
        "production_order_id": order.id,
    })
    WorkOrderService.start(company_id=company.id, work_order_id=wo.id)

    ex = OperationExecutionService.start(company_id=company.id, data={
        "work_order_id": wo.id, "operation_id": op.id,
        "work_center_id": wc.id,
    })
    # Плохое качество → rework
    ex = OperationExecutionService.record_quality(
        company_id=company.id, execution_id=ex.id,
        quality_results_json=[
            {"quality_point_id": qp.id, "is_passed": False, "comment": "Брак"},
        ],
    )
    assert ex.status == "rework"

    # Ручной возврат в работу
    # (в реальном сценарии — через новый start или прямой вызов)
    ex.status = "in_progress"
    ex.save()

    # Завершаем операцию
    ex = OperationExecutionService.complete(
        company_id=company.id, execution_id=ex.id,
    )
    assert ex.status == "completed"