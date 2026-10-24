import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.production.models import ProductionOrder


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="prod", email="p@test.co", password="x",
    )
    u.companies.add(company)
    u.current_company = company
    u.hr_employee_id = 10
    u.save()
    return u


@pytest.fixture
def api_client(api_user):
    c = APIClient()
    c.force_authenticate(user=api_user)
    return c


@pytest.mark.django_db
def test_create_production_order(api_client, company, bom, routing):
    r = api_client.post(
        "/api/v1/production/orders/",
        {
            "bom": bom.id, "routing": routing.id,
            "planned_quantity": 100,
        },
        format="json",
    )
    assert r.status_code == 201
    assert ProductionOrder.objects.filter(company=company).exists()


@pytest.mark.django_db
def test_confirm_order(api_client, company, bom, routing):
    order = ProductionOrder.objects.create(
        company=company, code="PROD-1", bom=bom, routing=routing,
        planned_quantity=100, status="draft",
    )
    r = api_client.post(f"/api/v1/production/orders/{order.id}/confirm/")
    assert r.status_code == 200
    order.refresh_from_db()
    assert order.status == "confirmed"


@pytest.mark.django_db
def test_record_quality_action(
    api_client, company, bom, routing, operation, quality_point,
):
    from apps.production.models import WorkOrder
    order = ProductionOrder.objects.create(
        company=company, code="PROD-1", bom=bom, routing=routing,
        planned_quantity=1, status="confirmed",
    )
    wo = WorkOrder.objects.create(
        company=company, code="WO-1",
        production_order=order, status="planned",
    )
    from apps.production.models import OperationExecution
    ex = OperationExecution.objects.create(
        company=company, code="EXEC-1", work_order=wo,
        operation=operation, status="in_progress",
    )
    r = api_client.post(
        f"/api/v1/production/executions/{ex.id}/record-quality/",
        {"quality_results_json": [
            {"quality_point_id": quality_point.id, "is_passed": True},
        ]},
        format="json",
    )
    assert r.status_code == 200
    ex.refresh_from_db()
    assert ex.status == "in_progress"  # хорошее качество