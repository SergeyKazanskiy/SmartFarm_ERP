"""
E2E по Finance_Scenarios.yml:
- SCENARIO-FIN-01: Procure-to-Pay (P2P)
- SCENARIO-FIN-02: Month-End Closing
"""
import pytest
from decimal import Decimal

from apps.finance.models import FinancialTransaction, Invoice, Payment
from apps.finance.services import (
    BudgetService, FinancialIndicatorService, FinancialPeriodService,
    InvoiceService, PaymentService,
)


@pytest.mark.django_db
def test_scenario_fin_001_p2p(
    company, accounts, counterparty, bank_account,
):
    """
    Полный цикл Procure-to-Pay:
    счёт (AP) → issued → платёж (planned) → complete →
    пересчёт status=paid + автопроводка Дт 60 Кт 51.
    """
    # 1. Создание AP-счёта
    inv = InvoiceService.create(company_id=company.id, data={
        "invoice_type": "AP",
        "counterparty_id": counterparty.id,
        "invoice_number": "FINV-2026-001",
        "invoice_date": "2026-06-01",
        "due_date": "2026-07-01",
        "amount": 625000,
        "currency_id": 1,
    })
    assert inv.status == "draft"

    # 2. Выставление
    inv = InvoiceService.issue(company_id=company.id, invoice_id=inv.id)
    assert inv.status == "issued"

    # 3. Планирование платежа
    payment = PaymentService.plan(company_id=company.id, data={
        "invoice_id": inv.id,
        "bank_account_id": bank_account.id,
        "payment_date": "2026-06-15T10:00:00Z",
        "amount": 625000,
    })
    assert payment.payment_status == "planned"

    # 4. Исполнение платежа
    payment = PaymentService.complete(
        company_id=company.id, payment_id=payment.id,
    )
    assert payment.payment_status == "completed"

    # 5. Проверка счёта
    inv.refresh_from_db()
    assert inv.status == "paid"

    # 6. Проверка проводки
    tx = FinancialTransaction.objects.get(
        company=company, payment=payment,
    )
    assert tx.debit_account.account_code == "60"
    assert tx.credit_account.account_code == "51"
    assert tx.amount == Decimal("625000.00")


@pytest.mark.django_db
def test_scenario_fin_002_month_end(company):
    """
    Закрытие месяца: период открыт → показатели внесены → период закрыт.
    """
    # 1. Создание периода
    period = FinancialPeriodService.create(company_id=company.id, data={
        "name": "Июнь 2026",
        "date_from": "2026-06-01",
        "date_to": "2026-06-30",
    })
    assert period.is_closed is False

    # 2. Внесение показателей
    FinancialIndicatorService.create(company_id=company.id, data={
        "period_id": period.id,
        "indicator_code": "revenue",
        "indicator_value": 275000,
    })
    FinancialIndicatorService.create(company_id=company.id, data={
        "period_id": period.id,
        "indicator_code": "cost_of_goods_sold",
        "indicator_value": 150000,
    })

    # 3. Закрытие
    period = FinancialPeriodService.close(
        company_id=company.id, period_id=period.id,
    )
    assert period.is_closed is True