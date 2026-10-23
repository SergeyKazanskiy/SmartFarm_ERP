import pytest
from decimal import Decimal

from core.event_bus import DomainEvent
from core.events import FinanceEvents as FE

from apps.finance.models import (
    FinancialTransaction, Invoice, Payment,
)
from apps.finance.services import (
    AccountService, BudgetService, InvoiceService, PaymentService,
)


@pytest.mark.django_db
def test_account_create_publishes_event(company):
    acc = AccountService.create(company_id=company.id, data={
        "account_code": "51", "account_name": "Деньги",
        "account_type": "asset",
    })
    assert DomainEvent.objects.filter(
        event_type=FE.ACCOUNT_CREATE, company=company,
    ).exists()


@pytest.mark.django_db
def test_budget_approve(company):
    b = BudgetService.create(company_id=company.id, data={
        "period_from": "2026-01-01", "period_to": "2026-12-31",
    })
    b = BudgetService.approve(
        company_id=company.id, budget_id=b.id, approver_employee_id=1,
    )
    assert b.status == "approved"


@pytest.mark.django_db
def test_invoice_issue_and_cancel(company, counterparty):
    inv = InvoiceService.create(company_id=company.id, data={
        "invoice_type": "AP", "counterparty_id": counterparty.id,
        "invoice_date": "2026-06-01", "amount": 100,
    })
    assert inv.status == "draft"

    inv = InvoiceService.issue(company_id=company.id, invoice_id=inv.id)
    assert inv.status == "issued"

    inv = InvoiceService.cancel(company_id=company.id, invoice_id=inv.id)
    assert inv.status == "cancelled"


@pytest.mark.django_db
def test_payment_complete_creates_transaction(
    company, accounts, ap_invoice, bank_account,
):
    """
    Ключевой тест: проведение AP-платежа создаёт проводку
    Дт 60 (AP) — Кт 51 (банк).
    """
    payment = PaymentService.plan(company_id=company.id, data={
        "invoice_id": ap_invoice.id,
        "bank_account_id": bank_account.id,
        "payment_date": "2026-06-15T10:00:00Z",
        "amount": 100000,
    })
    assert payment.payment_status == "planned"

    payment = PaymentService.complete(
        company_id=company.id, payment_id=payment.id,
    )
    assert payment.payment_status == "completed"

    ap_invoice.refresh_from_db()
    assert ap_invoice.status == "paid"

    tx = FinancialTransaction.objects.filter(
        company=company, payment=payment,
    ).first()
    assert tx is not None
    assert tx.debit_account.account_code == "60"
    assert tx.credit_account.account_code == "51"
    assert tx.amount == Decimal("100000.00")


@pytest.mark.django_db
def test_payment_complete_ar_creates_transaction(
    company, accounts, ar_invoice, bank_account,
):
    """
    AR-платёж: Дт 51 — Кт 62.
    """
    payment = PaymentService.plan(company_id=company.id, data={
        "invoice_id": ar_invoice.id,
        "bank_account_id": bank_account.id,
        "payment_date": "2026-06-15T10:00:00Z",
        "amount": 100000,
    })
    payment = PaymentService.complete(
        company_id=company.id, payment_id=payment.id,
    )

    tx = FinancialTransaction.objects.filter(
        company=company, payment=payment,
    ).first()
    assert tx.debit_account.account_code == "51"
    assert tx.credit_account.account_code == "62"


@pytest.mark.django_db
def test_partial_payment(company, accounts, ap_invoice, bank_account):
    """Частичная оплата → partially_paid."""
    payment = PaymentService.plan(company_id=company.id, data={
        "invoice_id": ap_invoice.id,
        "bank_account_id": bank_account.id,
        "payment_date": "2026-06-15T10:00:00Z",
        "amount": 40000,
    })
    PaymentService.complete(
        company_id=company.id, payment_id=payment.id,
    )
    ap_invoice.refresh_from_db()
    assert ap_invoice.status == "partially_paid"


@pytest.mark.django_db
def test_payment_cancel_only_planned(
    company, accounts, ap_invoice, bank_account,
):
    payment = PaymentService.plan(company_id=company.id, data={
        "invoice_id": ap_invoice.id,
        "bank_account_id": bank_account.id,
        "payment_date": "2026-06-15T10:00:00Z",
        "amount": 100,
    })
    PaymentService.complete(
        company_id=company.id, payment_id=payment.id,
    )
    with pytest.raises(ValueError):
        PaymentService.cancel(
            company_id=company.id, payment_id=payment.id,
        )


@pytest.mark.django_db
def test_no_transaction_without_accounts(company, counterparty, bank_account):
    """
    Если в плане нет кодов 60/51 — проводка не создаётся (тихо).
    """
    inv = Invoice.objects.create(
        company=company, code="FINV-X", invoice_type="AP",
        counterparty_id=counterparty.id,
        invoice_date="2026-06-01", amount=100, status="issued",
    )
    payment = PaymentService.plan(company_id=company.id, data={
        "invoice_id": inv.id,
        "bank_account_id": bank_account.id,
        "payment_date": "2026-06-15T10:00:00Z",
        "amount": 100,
    })
    PaymentService.complete(
        company_id=company.id, payment_id=payment.id,
    )
    assert FinancialTransaction.objects.filter(
        company=company, payment=payment,
    ).count() == 0