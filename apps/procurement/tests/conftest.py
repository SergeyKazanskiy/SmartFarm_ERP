import pytest

from apps.companies.models import Company
from apps.cp.models import Counterparty, CounterpartyType
from apps.procurement.models import Supplier


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def cp_type(company):
    return CounterpartyType.objects.create(
        company=company, code="CPT-P", name="Поставщик",
    )


@pytest.fixture
def counterparty(company, cp_type):
    return Counterparty.objects.create(
        company=company, code="CP-001", name="Поставщик X",
        counterparty_type=cp_type,
    )


@pytest.fixture
def supplier(company, counterparty):
    return Supplier.objects.create(
        company=company, code="SUP-001",
        counterparty_id=counterparty.id,
        rating=9, is_preferred=True,
    )