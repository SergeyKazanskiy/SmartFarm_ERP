import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.pm.models import Project


@pytest.fixture
def api_user(db, company):
    User = get_user_model()
    u = User.objects.create_user(
        username="pm", email="pm@test.co", password="x",
    )
    u.companies.add(company)
    u.current_company = company
    u.hr_employee_id = 1
    u.save()
    return u


@pytest.fixture
def api_client(api_user):
    c = APIClient()
    c.force_authenticate(user=api_user)
    return c


@pytest.mark.django_db
def test_list_projects(api_client, project):
    r = api_client.get("/api/v1/pm/projects/")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 1


@pytest.mark.django_db
def test_create_project(api_client, company, customer):
    r = api_client.post(
        "/api/v1/pm/projects/",
        {"name": "Из API", "customer_id": customer.id, "priority": 2},
        format="json",
    )
    assert r.status_code == 201
    assert Project.objects.filter(company=company, name="Из API").exists()


@pytest.mark.django_db
def test_update_status_action(api_client, project):
    r = api_client.post(
        f"/api/v1/pm/projects/{project.id}/update-status/",
        {"status": "active"}, format="json",
    )
    assert r.status_code == 200
    project.refresh_from_db()
    assert project.status == "active"


@pytest.mark.django_db
def test_complete_project_action(api_client, project):
    project.status = "active"
    project.save()
    r = api_client.post(f"/api/v1/pm/projects/{project.id}/complete/")
    assert r.status_code == 200
    project.refresh_from_db()
    assert project.status == "completed"