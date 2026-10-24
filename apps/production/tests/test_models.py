import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.production.models import (
    Bom, OperationDefinition, ProductionOrder, Routing, WorkCenter,
)


@pytest.mark.django_db
def test_technology_code_unique(company):
    from apps.production.models import Technology
    Technology.objects.create(company=company, code="TECH-X", name="A")
    with pytest.raises(IntegrityError):
        Technology.objects.create(company=company, code="TECH-X", name="B")


@pytest.mark.django_db
def test_routing_protected_from_technology_delete(technology):
    Routing.objects.create(
        company=technology.company, code="ROUT-1",
        technology=technology, name="R1",
    )
    with pytest.raises(ProtectedError):
        technology.delete()


@pytest.mark.django_db
def test_operations_cascade_on_routing_delete(routing, operation):
    routing.delete()
    assert not OperationDefinition.objects.filter(pk=operation.pk).exists()


@pytest.mark.django_db
def test_bom_protects_operation_execution(
    company, bom, operation, work_center,
):
    """ProductionOrder использует PROTECT на OperationDefinition/WorkOrder."""
    from apps.production.models import ProductionOrder
    ProductionOrder.objects.create(
        company=company, code="PROD-1", bom=bom,
        planned_quantity=10, status="draft",
    )
    with pytest.raises(ProtectedError):
        bom.delete()


@pytest.mark.django_db
def test_quality_points_cascade(operation, quality_point):
    operation.delete()
    assert not quality_point.__class__.objects.filter(
        pk=quality_point.pk,
    ).exists()


@pytest.mark.django_db
def test_json_fields_accept_lists(company, routing, work_center):
    op = OperationDefinition.objects.create(
        company=company, code="OPDEF-X", routing=routing,
        name="Test", sequence_no=99, work_center=work_center,
        resources_json=[{"resource_type": "employee", "quantity": 1}],
        parameters_json=[{"name": "p", "target_value": 1, "tolerance": 0}],
    )
    op.refresh_from_db()
    assert isinstance(op.resources_json, list)
    assert op.resources_json[0]["resource_type"] == "employee"