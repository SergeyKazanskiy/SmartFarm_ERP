import pytest
from decimal import Decimal

from apps.production.models import (
    OperationExecution, ProductionOrder, WorkOrder,
)
from apps.production.services import (
    OperationExecutionService, OperationService,
    ProductionOrderService, WorkOrderService,
)


@pytest.mark.django_db
def test_production_order_confirm(company, bom, routing):
    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": routing.id,
        "planned_quantity": 100,
    })
    assert order.status == "draft"

    order = ProductionOrderService.confirm(
        company_id=company.id, production_order_id=order.id,
    )
    assert order.status == "confirmed"


@pytest.mark.django_db
def test_wo_start_auto_transitions_order(company, bom, routing):
    """
    Ключевой тест: запуск первого наряда переводит ProductionOrder
    в in_progress (OP-PROD-28 → OP-PROD-24).
    """
    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": routing.id,
        "planned_quantity": 100,
    })
    ProductionOrderService.confirm(
        company_id=company.id, production_order_id=order.id,
    )
    order.refresh_from_db()
    assert order.status == "confirmed"

    wo = WorkOrderService.create(company_id=company.id, data={
        "production_order_id": order.id,
    })
    assert wo.status == "planned"

    wo = WorkOrderService.start(company_id=company.id, work_order_id=wo.id)
    assert wo.status == "in_progress"
    order.refresh_from_db()
    assert order.status == "in_progress"


@pytest.mark.django_db
def test_order_complete_requires_all_wo_completed(
    company, bom, routing,
):
    """Нельзя закрыть заказ, пока есть незавершённые наряды."""
    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": routing.id,
        "planned_quantity": 10,
    })
    ProductionOrderService.confirm(
        company_id=company.id, production_order_id=order.id,
    )
    wo = WorkOrderService.create(company_id=company.id, data={
        "production_order_id": order.id,
    })
    WorkOrderService.start(company_id=company.id, work_order_id=wo.id)

    with pytest.raises(ValueError):
        ProductionOrderService.complete(
            company_id=company.id, production_order_id=order.id,
        )

    WorkOrderService.complete(company_id=company.id, work_order_id=wo.id)
    order = ProductionOrderService.complete(
        company_id=company.id, production_order_id=order.id,
    )
    assert order.status == "completed"


@pytest.mark.django_db
def test_operation_execution_auto_rework(
    company, bom, routing, operation, quality_point,
):
    """
    Плохое качество (is_passed=false) → автоматический перевод в rework.
    """
    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": routing.id, "planned_quantity": 1,
    })
    wo = WorkOrderService.create(company_id=company.id, data={
        "production_order_id": order.id,
    })

    ex = OperationExecutionService.start(company_id=company.id, data={
        "work_order_id": wo.id, "operation_id": operation.id,
    })
    assert ex.status == "in_progress"

    ex = OperationExecutionService.record_quality(
        company_id=company.id, execution_id=ex.id,
        quality_results_json=[
            {"quality_point_id": quality_point.id, "is_passed": False},
        ],
    )
    assert ex.status == "rework"


@pytest.mark.django_db
def test_operation_execution_good_quality(
    company, bom, routing, operation, quality_point,
):
    """Хорошее качество → остаётся in_progress."""
    order = ProductionOrderService.create(company_id=company.id, data={
        "bom_id": bom.id, "routing_id": routing.id, "planned_quantity": 1,
    })
    wo = WorkOrderService.create(company_id=company.id, data={
        "production_order_id": order.id,
    })
    ex = OperationExecutionService.start(company_id=company.id, data={
        "work_order_id": wo.id, "operation_id": operation.id,
    })
    ex = OperationExecutionService.record_quality(
        company_id=company.id, execution_id=ex.id,
        quality_results_json=[
            {"quality_point_id": quality_point.id, "is_passed": True},
        ],
    )
    assert ex.status == "in_progress"


@pytest.mark.django_db
def test_operation_update_resources(company, operation):
    op = OperationService.update_resources(
        company_id=company.id, operation_id=operation.id,
        resources_json=[{"resource_type": "asset", "quantity": 1}],
    )
    op.refresh_from_db()
    assert op.resources_json[0]["resource_type"] == "asset"