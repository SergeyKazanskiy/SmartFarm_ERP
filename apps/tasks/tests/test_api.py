"""
Тест DRF API: получение задач, начало, завершение.
"""
import pytest
from rest_framework.test import APIClient

from apps.tasks.models import TaskTask


@pytest.mark.django_db
def test_list_my_tasks(user, company):
    TaskTask.objects.create(
        company=company, task_name="Test task",
        assigned_role="", status="created",
    )

    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/v1/tasks/my/")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


@pytest.mark.django_db
def test_start_task(user, company):
    task = TaskTask.objects.create(
        company=company, task_name="T", status="created",
        assigned_role="",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(f"/api/v1/tasks/my/{task.id}/start/")
    assert response.status_code == 200
    task.refresh_from_db()
    assert task.status == "in_progress"