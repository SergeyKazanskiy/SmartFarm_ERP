import pytest

from apps.companies.models import Company
from apps.cp.models import Counterparty, CounterpartyType
from apps.crm.models import (
    Lead, LeadSource, LeadStatus, Opportunity, OpportunityStage,
)


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def cp_type(company):
    return CounterpartyType.objects.create(
        company=company, code="CPT-001", name="Клиент",
    )


@pytest.fixture
def counterparty(company, cp_type):
    return Counterparty.objects.create(
        company=company, code="CP-001", name="ООО Тест",
        counterparty_type=cp_type,
    )


@pytest.fixture
def lead_status(company):
    return LeadStatus.objects.create(
        company=company, code="LSTAT-001", name="Новый",
    )


@pytest.fixture
def lead_source(company):
    return LeadSource.objects.create(
        company=company, code="LS-001", name="Сайт",
    )


@pytest.fixture
def opp_stage(company):
    return OpportunityStage.objects.create(
        company=company, code="OST-001", name="Первичный контакт",
    )


@pytest.fixture
def lead(company, lead_status, lead_source):
    return Lead.objects.create(
        company=company, code="LEAD-001", title="Тест",
        lead_status=lead_status, lead_source=lead_source,
        responsible_employee_id=10,
    )


@pytest.fixture
def opportunity(company, lead, opp_stage):
    return Opportunity.objects.create(
        company=company, code="OPP-001", lead=lead,
        opportunity_stage=opp_stage, responsible_employee_id=10,
        amount=100000,
    )