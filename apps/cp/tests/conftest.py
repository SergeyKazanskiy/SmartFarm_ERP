import pytest

from apps.companies.models import Company
from apps.cp.models import Category, Counterparty, CounterpartyType


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def cp_type(company):
    return CounterpartyType.objects.create(
        company=company, code="CPT-001", name="Клиент",
    )


@pytest.fixture
def category(company):
    return Category.objects.create(
        company=company, code="CAT-001", name="VIP",
    )


@pytest.fixture
def counterparty(company, cp_type, category):
    return Counterparty.objects.create(
        company=company, code="CP-001", internal_code="CUST-001",
        name="ООО Тест", counterparty_type=cp_type, category=category,
    )