"""
Демо-команда: загружает Finance_test_data.json.

Использование:
    python manage.py demo_finance --company=1
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import FinanceEvents as FE

from apps.cp.models import Counterparty
from apps.finance.models import (
    BankAccount, Budget, BudgetItem, CashAccount, CostCenter,
    ExchangeRate, FinAccount, FinancialIndicator, FinancialPeriod,
    FinancialProject, FinancialTransaction, Invoice, InvoiceLine, Payment,
)


class Command(BaseCommand):
    help = "Загружает тестовые данные Finance"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/finance/workflow/Finance_test_data.json",
        )
        parser.add_argument("--emit-events", action="store_true", default=True)

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(pk=options["company"])
        except Company.DoesNotExist:
            raise CommandError(f"Company {options['company']} not found")

        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tables = data.get("tables", {})
        counters = {}

        with transaction.atomic():
            # Порядок: справочники → проекты/бюджеты → счета → платежи → проводки
            counters["account"] = self._load_accounts(
                company, tables.get("fin_account", []),
            )
            counters["cost_center"] = self._load_cost_centers(
                company, tables.get("fin_cost_center", []),
            )
            counters["financial_project"] = self._load_financial_projects(
                company, tables.get("fin_financial_project", []),
            )
            counters["budget"] = self._load_budgets(
                company, tables.get("fin_budget", []),
            )
            counters["budget_item"] = self._load_budget_items(
                company, tables.get("fin_budget_item", []),
            )
            counters["cash_account"] = self._load_cash_accounts(
                company, tables.get("fin_cash_account", []),
            )
            counters["bank_account"] = self._load_bank_accounts(
                company, tables.get("fin_bank_account", []),
            )
            counters["invoice"] = self._load_invoices(
                company, tables.get("fin_invoice", []),
            )
            counters["invoice_line"] = self._load_invoice_lines(
                company, tables.get("fin_invoice_line", []),
            )
            counters["payment"] = self._load_payments(
                company, tables.get("fin_payment", []),
            )
            counters["transaction"] = self._load_transactions(
                company, tables.get("fin_financial_transaction", []),
            )
            counters["period"] = self._load_periods(
                company, tables.get("fin_financial_period", []),
            )
            counters["indicator"] = self._load_indicators(
                company, tables.get("fin_financial_indicator", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные Finance загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # ------------------------------------------------------------------
    # Загрузчики
    # ------------------------------------------------------------------

    def _load_accounts(self, company, rows) -> int:
        n = 0
        for r in rows:
            FinAccount.objects.update_or_create(
                company=company, code=r["account_id"],
                defaults={
                    "account_code": r["account_code"],
                    "account_name": r["account_name"],
                    "account_type": r.get("account_type", ""),
                },
            )
            n += 1
        return n

    def _load_cost_centers(self, company, rows) -> int:
        n = 0
        for r in rows:
            CostCenter.objects.update_or_create(
                company=company, code=r["cost_center_id"],
                defaults={"name": r["cost_center_name"]},
            )
            n += 1
        return n

    def _load_financial_projects(self, company, rows) -> int:
        n = 0
        for r in rows:
            FinancialProject.objects.update_or_create(
                company=company, code=r["financial_project_id"],
                defaults={
                    "name": r["financial_project_name"],
                    "linked_object_type": r.get("linked_object_type", ""),
                    "linked_object_id": _parse_int_id(r.get("linked_object_id")),
                },
            )
            n += 1
        return n

    def _load_budgets(self, company, rows) -> int:
        n = 0
        for r in rows:
            fp = None
            if r.get("financial_project_id"):
                fp = FinancialProject.objects.filter(
                    company=company, code=r["financial_project_id"],
                ).first()
            Budget.objects.update_or_create(
                company=company, code=r["budget_id"],
                defaults={
                    "financial_project": fp,
                    "period_from": r["period_from"],
                    "period_to": r["period_to"],
                    "status": r.get("status_id", "draft"),
                },
            )
            n += 1
        return n

    def _load_budget_items(self, company, rows) -> int:
        n = 0
        for r in rows:
            b = Budget.objects.get(company=company, code=r["budget_id"])
            cc = (
                CostCenter.objects.filter(
                    company=company, code=r["cost_center_id"],
                ).first()
                if r.get("cost_center_id") else None
            )
            BudgetItem.objects.update_or_create(
                company=company, code=r["budget_item_id"],
                defaults={
                    "budget": b,
                    "cost_center": cc,
                    "planned_amount": r["planned_amount"],
                },
            )
            n += 1
        return n

    def _load_cash_accounts(self, company, rows) -> int:
        n = 0
        for r in rows:
            CashAccount.objects.update_or_create(
                company=company, code=r["cash_account_id"],
                defaults={"name": r["cash_account_name"]},
            )
            n += 1
        return n

    def _load_bank_accounts(self, company, rows) -> int:
        n = 0
        for r in rows:
            BankAccount.objects.update_or_create(
                company=company, code=r["bank_account_id"],
                defaults={
                    "bank_id": _parse_int_id(r.get("bank_id")),
                    "account_number": r["account_number"],
                    "currency_id": _parse_int_id(r.get("currency_id")),
                },
            )
            n += 1
        return n

    def _load_invoices(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp_id = self._resolve_cp(r.get("counterparty_id"), company)
            Invoice.objects.update_or_create(
                company=company, code=r["invoice_id"],
                defaults={
                    "invoice_type": r["invoice_type"],
                    "counterparty_id": cp_id or 0,
                    "contract_id": _parse_int_id(r.get("contract_id")),
                    "source_object_type": r.get("source_object_type", ""),
                    "source_object_id": _parse_int_id(r.get("source_object_id")),
                    "invoice_number": r.get("invoice_number", ""),
                    "invoice_date": r["invoice_date"],
                    "due_date": r.get("due_date"),
                    "amount": r["amount"],
                    "currency_id": _parse_int_id(r.get("currency_id")),
                    "status": r.get("status_id", "draft"),
                },
            )
            n += 1
        return n

    def _load_invoice_lines(self, company, rows) -> int:
        n = 0
        for r in rows:
            inv = Invoice.objects.get(company=company, code=r["invoice_id"])
            InvoiceLine.objects.update_or_create(
                company=company, code=r["invoice_line_id"],
                defaults={
                    "invoice": inv,
                    "description": r["description"],
                    "amount": r["amount"],
                },
            )
            n += 1
        return n

    def _load_payments(self, company, rows) -> int:
        n = 0
        for r in rows:
            inv = (
                Invoice.objects.filter(
                    company=company, code=r["invoice_id"],
                ).first()
                if r.get("invoice_id") else None
            )
            bank = (
                BankAccount.objects.filter(
                    company=company, code=r["bank_account_id"],
                ).first()
                if r.get("bank_account_id") else None
            )
            cash = (
                CashAccount.objects.filter(
                    company=company, code=r["cash_account_id"],
                ).first()
                if r.get("cash_account_id") else None
            )
            Payment.objects.update_or_create(
                company=company, code=r["payment_id"],
                defaults={
                    "invoice": inv,
                    "bank_account": bank,
                    "cash_account": cash,
                    "payment_status": r.get("payment_status", "planned"),
                    "payment_date": r["payment_date"],
                    "amount": r["amount"],
                },
            )
            n += 1
        return n

    def _load_transactions(self, company, rows) -> int:
        n = 0
        for r in rows:
            debit = FinAccount.objects.get(
                company=company, code=r["debit_account_id"],
            )
            credit = FinAccount.objects.get(
                company=company, code=r["credit_account_id"],
            )
            cc = (
                CostCenter.objects.filter(
                    company=company, code=r["cost_center_id"],
                ).first()
                if r.get("cost_center_id") else None
            )
            payment = (
                Payment.objects.filter(
                    company=company, code=r["payment_id"],
                ).first()
                if r.get("payment_id") else None
            )
            FinancialTransaction.objects.update_or_create(
                company=company, code=r["transaction_id"],
                defaults={
                    "debit_account": debit,
                    "credit_account": credit,
                    "cost_center": cc,
                    "payment": payment,
                    "amount": r["amount"],
                    "transaction_date": r["transaction_date"],
                },
            )
            n += 1
        return n

    def _load_periods(self, company, rows) -> int:
        n = 0
        for r in rows:
            FinancialPeriod.objects.update_or_create(
                company=company, code=r["period_id"],
                defaults={
                    "name": r["period_name"],
                    "date_from": r["date_from"],
                    "date_to": r["date_to"],
                    "is_closed": bool(r.get("is_closed", 0)),
                },
            )
            n += 1
        return n

    def _load_indicators(self, company, rows) -> int:
        n = 0
        for r in rows:
            fp = (
                FinancialProject.objects.filter(
                    company=company, code=r["financial_project_id"],
                ).first()
                if r.get("financial_project_id") else None
            )
            period = (
                FinancialPeriod.objects.filter(
                    company=company, code=r["period_id"],
                ).first()
                if r.get("period_id") else None
            )
            FinancialIndicator.objects.update_or_create(
                company=company, code=r["indicator_id"],
                defaults={
                    "financial_project": fp,
                    "period": period,
                    "indicator_code": r["indicator_code"],
                    "indicator_value": r.get("indicator_value"),
                },
            )
            n += 1
        return n

    # ------------------------------------------------------------------
    # Утилиты
    # ------------------------------------------------------------------

    def _resolve_cp(self, code: str | None, company) -> int | None:
        """'CP-005' → Counterparty.id."""
        if not code:
            return None
        cp = Counterparty.objects.filter(company=company, code=code).first()
        return cp.id if cp else None

    def _emit_events(self, company) -> None:
        for inv in Invoice.objects.filter(company=company):
            EventBus.publish(
                FE.INVOICE_CREATE,
                company_id=company.id,
                payload={
                    "invoice_id": inv.id,
                    "invoice_type": inv.invoice_type,
                    "counterparty_id": inv.counterparty_id,
                    "amount": float(inv.amount),
                },
            )


def _parse_int_id(value) -> int | None:
    """'BANK-001' → 1; 'CUR-001' → 1; 'PROD-001' → 1; None → None."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        for prefix in ("EMP-", "MAT-", "CUR-", "ADDR-", "BANK-", "PROD-", "POS-", "NP-", "DOC-", "SO-", "PO-"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None