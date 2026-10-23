import pytest

from apps.companies.models import Company
from apps.cp.models import Counterparty, CounterpartyType
from apps.pm.models import Project


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def cp_type(company):
    return CounterpartyType.objects.create(
        company=company, code="CPT-001", name="Клиент",
    )


@pytest.fixture
def customer(company, cp_type):
    return Counterparty.objects.create(
        company=company, code="CP-001", name="Заказчик",
        counterparty_type=cp_type,
    )


@pytest.fixture
def project(company, customer):
    return Project.objects.create(
        company=company, code="PROJ-001",
        name="Тестовый проект",
        customer_id=customer.id,
        status="planning",
        priority=1,
    )