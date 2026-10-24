import pytest

from apps.companies.models import Company
from apps.production.models import (
    Bom, BomItem, OperationDefinition, QualityPoint,
    Routing, Technology, WorkCenter,
)


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def technology(company):
    return Technology.objects.create(
        company=company, code="TECH-001", name="Сборка",
    )


@pytest.fixture
def work_center(company):
    return WorkCenter.objects.create(
        company=company, code="WC-001", name="Участок 1",
    )


@pytest.fixture
def routing(company, technology):
    return Routing.objects.create(
        company=company, code="ROUT-001",
        technology=technology, name="Маршрут 1",
    )


@pytest.fixture
def operation(company, routing, work_center):
    return OperationDefinition.objects.create(
        company=company, code="OPDEF-001",
        routing=routing, name="Сборка корпуса",
        sequence_no=1, work_center=work_center,
        resources_json=[{"resource_type": "employee", "quantity": 2}],
        parameters_json=[{"name": "temperature", "target_value": 22, "tolerance": 2}],
    )


@pytest.fixture
def quality_point(company, operation):
    return QualityPoint.objects.create(
        company=company, code="QP-001",
        operation=operation, name="Проверка зазоров",
    )


@pytest.fixture
def bom(company):
    return Bom.objects.create(
        company=company, code="BOM-001",
        product_material_id=6, name="SmartTV X-100",
    )


@pytest.fixture
def bom_item(company, bom):
    return BomItem.objects.create(
        company=company, code="BOMI-001",
        bom=bom, material_id=1, quantity=1, unit_cost=145,
    )