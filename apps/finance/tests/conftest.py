import pytest

from apps.companies.models import Company
from apps.cp.models import Counterparty, CounterpartyType
from apps.finance.models import (
    BankAccount, CashAccount, CostCenter, FinAccount, Invoice,
)


@pytest.fixture
def company(db):
    return Company.objects.create(code="COMP-001", name="Test Co")


@pytest.fixture
def cp_type(company):
    return CounterpartyType.objects.create(
        company=company, code="CPT-F", name="Поставщик",
    )


@pytest.fixture
def counterparty(company, cp_type):
    return Counterparty.objects.create(
        company=company, code="CP-001", name="Контрагент",
        counterparty_type=cp_type,
    )


@pytest.fixture
def accounts(company):
    """План счетов: 51 (банк), 60 (AP), 62 (AR)."""
    return {
        "bank": FinAccount.objects.create(
            company=company, code="ACC-51", account_code="51",
            account_name="Денежные средства", account_type="asset",
        ),
        "ap": FinAccount.objects.create(
            company=company, code="ACC-60", account_code="60",
            account_name="Расчёты с поставщиками", account_type="liability",
        ),
        "ar": FinAccount.objects.create(
            company=company, code="ACC-62", account_code="62",
            account_name="Расчёты с покупателями", account_type="asset",
        ),
    }


@pytest.fixture
def bank_account(company):
    return BankAccount.objects.create(
        company=company, code="BANK-001",
        account_number="UA1234", currency_id=1,
    )


@pytest.fixture
def cash_account(company):
    return CashAccount.objects.create(
        company=company, code="CASH-001", name="Основная касса",
    )


@pytest.fixture
def cost_center(company):
    return CostCenter.objects.create(
        company=company, code="CC-001", name="Цех 1",
    )


@pytest.fixture
def ap_invoice(company, counterparty):
    return Invoice.objects.create(
        company=company, code="FINV-AP", invoice_type="AP",
        counterparty_id=counterparty.id,
        invoice_number="INV-1", invoice_date="2026-06-01",
        amount=100000, currency_id=1, status="issued",
    )


@pytest.fixture
def ar_invoice(company, counterparty):
    return Invoice.objects.create(
        company=company, code="FINV-AR", invoice_type="AR",
        counterparty_id=counterparty.id,
        invoice_number="INV-2", invoice_date="2026-06-01",
        amount=100000, currency_id=1, status="issued",
    )