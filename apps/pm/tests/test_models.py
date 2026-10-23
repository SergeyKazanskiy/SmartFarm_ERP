import pytest
from django.db import IntegrityError

from apps.pm.models import Phase, Task, TaskDependency


@pytest.mark.django_db
def test_project_code_unique(company, customer):
    from apps.pm.models import Project
    Project.objects.create(
        company=company, code="PROJ-X", name="A", customer_id=customer.id,
    )
    with pytest.raises(IntegrityError):
        Project.objects.create(
            company=company, code="PROJ-X", name="B", customer_id=customer.id,
        )


@pytest.mark.django_db
def test_cascade_delete_phases(project):
    phase = Phase.objects.create(
        company=project.company, code="PHASE-001",
        project=project, name="Этап 1",
    )
    project.delete()
    assert not Phase.objects.filter(pk=phase.pk).exists()


@pytest.mark.django_db
def test_cascade_delete_tasks(project):
    task = Task.objects.create(
        company=project.company, code="PTASK-001",
        project=project, name="Задача",
    )
    project.delete()
    assert not Task.objects.filter(pk=task.pk).exists()


@pytest.mark.django_db
def test_self_ref_phase_set_null(project):
    parent = Phase.objects.create(
        company=project.company, code="PHASE-P", project=project, name="Parent",
    )
    child = Phase.objects.create(
        company=project.company, code="PHASE-C", project=project,
        name="Child", parent=parent,
    )
    parent.delete()
    child.refresh_from_db()
    assert child.parent is None


@pytest.mark.django_db
def test_dependency_unique_pair(project):
    t1 = Task.objects.create(
        company=project.company, code="PT-1", project=project, name="A",
    )
    t2 = Task.objects.create(
        company=project.company, code="PT-2", project=project, name="B",
    )
    TaskDependency.objects.create(
        company=project.company, code="DEP-1",
        predecessor=t1, successor=t2, dependency_type="FS",
    )
    with pytest.raises(IntegrityError):
        TaskDependency.objects.create(
            company=project.company, code="DEP-2",
            predecessor=t1, successor=t2, dependency_type="FS",
        )