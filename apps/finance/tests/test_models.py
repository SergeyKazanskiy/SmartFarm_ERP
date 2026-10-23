import pytest
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.finance.models import (
    FinancialTransaction, Invoice, Payment,
)


@pytest.mark.django_db
def test_account_code_unique(company, accounts):
    from apps.finance.models import FinAccount
    with pytest.raises(IntegrityError):
        FinAccount.objects.create(
            company=company, code="ACC-DUP", account_code="51",
            account_name="Дубликат", account_type="asset",
        )


@pytest.mark.django_db
def test_check_constraint_debit_ne_credit(company, accounts):
    """Проводка Дт == Кт запрещена."""
    with pytest.raises(IntegrityError):
        FinancialTransaction.objects.create(
            company=company, code="FT-BAD",
            debit_account=accounts["ap"],
            credit_account=accounts["ap"],
            amount=100, transaction_date="2026-01-01T00:00:00Z",
        )


@pytest.mark.django_db
def test_protect_account_with_transaction(company, accounts, bank_account):
    """Нельзя удалить счёт, на который есть проводка."""
    payment = Payment.objects.create(
        company=company, code="PAY-1", bank_account=bank_account,
        payment_status="completed", payment_date="2026-01-01T00:00:00Z",
        amount=100,
    )
    FinancialTransaction.objects.create(
        company=company, code="FT-1",
        debit_account=accounts["ap"], credit_account=accounts["bank"],
        payment=payment, amount=100, transaction_date="2026-01-01T00:00:00Z",
    )
    with pytest.raises(ProtectedError):
        accounts["ap"].delete()


@pytest.mark.django_db
def test_protect_invoice_with_payment(company, ap_invoice, bank_account):
    Payment.objects.create(
        company=company, code="PAY-1", invoice=ap_invoice,
        bank_account=bank_account, payment_status="planned",
        payment_date="2026-01-01T00:00:00Z", amount=100,
    )
    with pytest.raises(ProtectedError):
        ap_invoice.delete()


@pytest.mark.django_db
def test_invoice_lines_cascade_on_invoice_delete(company, ap_invoice):
    from apps.finance.models import InvoiceLine
    line = InvoiceLine.objects.create(
        company=company, code="FINVL-1", invoice=ap_invoice,
        description="X", amount=100,
    )
    ap_invoice.delete()
    assert not InvoiceLine.objects.filter(pk=line.pk).exists()