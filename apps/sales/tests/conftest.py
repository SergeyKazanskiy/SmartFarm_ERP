import pytest

from apps.companies.models import Company
from apps.cp.models import Counterparty, CounterpartyType
from apps.sales.models import Customer, PriceList, PriceListLine


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def cp_type(company):
    return CounterpartyType.objects.create(
        company=company, code="CPT-S", name="Клиент",
    )


@pytest.fixture
def counterparty(company, cp_type):
    return Counterparty.objects.create(
        company=company, code="CP-001", name="Заказчик",
        counterparty_type=cp_type,
    )


@pytest.fixture
def price_list(company):
    return PriceList.objects.create(
        company=company, code="PL-001", name="Стандарт", is_default=True,
    )


@pytest.fixture
def price_list_line(company, price_list):
    return PriceListLine.objects.create(
        company=company, code="PLL-001", price_list=price_list,
        material_id=6, unit_price=5500,
    )


@pytest.fixture
def customer(company, counterparty):
    return Customer.objects.create(
        company=company, code="CUST-001",
        counterparty_id=counterparty.id,
        category="VIP", credit_limit=500000,
    )