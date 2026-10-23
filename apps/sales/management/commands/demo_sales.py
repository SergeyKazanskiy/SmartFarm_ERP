"""
Демо-команда: загружает Sales_test_data.json.

Использование:
    python manage.py demo_sales --company=1
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.cp.models import Counterparty
from apps.sales.models import (
    Customer, Invoice, Opportunity, Order, OrderLine,
    PriceList, PriceListLine, Quote, QuoteLine, Shipment,
)


class Command(BaseCommand):
    help = "Загружает тестовые данные Sales"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/sales/workflow/Sales_test_data.json",
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
            # Порядок важен: сначала справочники, потом документы
            counters["price_list"] = self._load_price_lists(
                company, tables.get("sales_price_list", []),
            )
            counters["price_list_line"] = self._load_price_list_lines(
                company, tables.get("sales_price_list_line", []),
            )
            counters["customer"] = self._load_customers(
                company, tables.get("sales_customer", []),
            )
            counters["opportunity"] = self._load_opportunities(
                company, tables.get("sales_opportunity", []),
            )
            counters["quote"] = self._load_quotes(
                company, tables.get("sales_quote", []),
            )
            counters["quote_line"] = self._load_quote_lines(
                company, tables.get("sales_quote_line", []),
            )
            counters["order"] = self._load_orders(
                company, tables.get("sales_order", []),
            )
            counters["order_line"] = self._load_order_lines(
                company, tables.get("sales_order_line", []),
            )
            counters["invoice"] = self._load_invoices(
                company, tables.get("sales_invoice", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные Sales загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # ------------------------------------------------------------------
    # Загрузчики
    # ------------------------------------------------------------------

    def _load_price_lists(self, company, rows) -> int:
        n = 0
        for r in rows:
            PriceList.objects.update_or_create(
                company=company, code=r["price_list_id"],
                defaults={
                    "name": r["price_list_name"],
                    "currency_id": _parse_int_id(r.get("currency_id")),
                    "valid_from": r.get("valid_from"),
                    "valid_to": r.get("valid_to"),
                    "is_default": r.get("is_default", False),
                },
            )
            n += 1
        return n

    def _load_price_list_lines(self, company, rows) -> int:
        n = 0
        for r in rows:
            pl = PriceList.objects.get(company=company, code=r["price_list_id"])
            PriceListLine.objects.update_or_create(
                company=company, code=r["price_line_id"],
                defaults={
                    "price_list": pl,
                    "material_id": _parse_int_id(r["material_id"]) or 0,
                    "unit_price": r["unit_price"],
                    "min_quantity": r.get("min_quantity"),
                },
            )
            n += 1
        return n

    def _load_customers(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp_id = self._resolve_cp(r.get("counterparty_id"), company)
            pl = (
                PriceList.objects.filter(
                    company=company, code=r["default_price_list_id"],
                ).first()
                if r.get("default_price_list_id") else None
            )
            Customer.objects.update_or_create(
                company=company, code=r["customer_id"],
                defaults={
                    "counterparty_id": cp_id or 0,
                    "category": r.get("customer_category", ""),
                    "credit_limit": r.get("credit_limit"),
                    "payment_terms": r.get("payment_terms", ""),
                    "default_price_list": pl,
                    "sales_manager_employee_id": _parse_int_id(
                        r.get("sales_manager_employee_id")
                    ),
                    "is_active": r.get("is_active", True),
                },
            )
            n += 1
        return n

    def _load_opportunities(self, company, rows) -> int:
        n = 0
        for r in rows:
            customer = Customer.objects.get(company=company, code=r["customer_id"])
            Opportunity.objects.update_or_create(
                company=company, code=r["opportunity_id"],
                defaults={
                    "customer": customer,
                    "name": r["opportunity_name"],
                    "stage": r.get("stage_id", "lead"),
                    "expected_value": r.get("expected_value"),
                    "probability_percent": r.get("probability_percent"),
                    "expected_close_date": r.get("expected_close_date"),
                    "created_by_employee_id": _parse_int_id(
                        r.get("created_by_employee_id")
                    ),
                },
            )
            n += 1
        return n

    def _load_quotes(self, company, rows) -> int:
        n = 0
        for r in rows:
            customer = Customer.objects.get(company=company, code=r["customer_id"])
            opp = (
                Opportunity.objects.filter(
                    company=company, code=r["opportunity_id"],
                ).first() if r.get("opportunity_id") else None
            )
            Quote.objects.update_or_create(
                company=company, code=r["quote_id"],
                defaults={
                    "quote_number": r["quote_number"],
                    "customer": customer,
                    "opportunity": opp,
                    "quote_date": r["quote_date"],
                    "valid_until": r.get("valid_until"),
                    "total_amount": r.get("total_amount"),
                    "status": r.get("status_id", "draft"),
                    "created_by_employee_id": _parse_int_id(
                        r.get("created_by_employee_id")
                    ),
                },
            )
            n += 1
        return n

    def _load_quote_lines(self, company, rows) -> int:
        n = 0
        for r in rows:
            quote = Quote.objects.get(company=company, code=r["quote_id"])
            pli = None
            if r.get("price_list_item_id"):
                pli = PriceListLine.objects.filter(
                    company=company, code=r["price_list_item_id"],
                ).first()
            QuoteLine.objects.update_or_create(
                company=company, code=r["quote_line_id"],
                defaults={
                    "quote": quote,
                    "material_id": _parse_int_id(r["material_id"]) or 0,
                    "price_list_item": pli,
                    "quantity": r["quantity"],
                    "unit_price": r["unit_price"],
                    "discount_percent": r.get("discount_percent", 0),
                    "total_price": r.get("total_price"),
                },
            )
            n += 1
        return n

    def _load_orders(self, company, rows) -> int:
        n = 0
        for r in rows:
            customer = Customer.objects.get(company=company, code=r["customer_id"])
            quote = (
                Quote.objects.filter(
                    company=company, code=r["quote_id"],
                ).first() if r.get("quote_id") else None
            )
            Order.objects.update_or_create(
                company=company, code=r["order_id"],
                defaults={
                    "order_number": r["order_number"],
                    "customer": customer,
                    "quote": quote,
                    "order_date": r["order_date"],
                    "order_type": r.get("order_type", "regular"),
                    "status": r.get("status_id", "draft"),
                    "total_amount": r.get("total_amount"),
                    "currency_id": _parse_int_id(r.get("currency_id")),
                    "expected_ship_date": r.get("expected_ship_date"),
                    "actual_ship_date": r.get("actual_ship_date"),
                    "delivery_address_id": _parse_int_id(r.get("delivery_address_id")),
                    "created_by_employee_id": _parse_int_id(
                        r.get("created_by_employee_id")
                    ),
                    "production_order_id": _parse_int_id(r.get("production_order_id")),
                },
            )
            n += 1
        return n

    def _load_order_lines(self, company, rows) -> int:
        n = 0
        for r in rows:
            order = Order.objects.get(company=company, code=r["order_id"])
            OrderLine.objects.update_or_create(
                company=company, code=r["order_line_id"],
                defaults={
                    "order": order,
                    "material_id": _parse_int_id(r["material_id"]) or 0,
                    "quantity": r["quantity"],
                    "unit_price": r["unit_price"],
                    "discount_percent": r.get("discount_percent", 0),
                    "total_price": r.get("total_price"),
                    "shipped_quantity": r.get("shipped_quantity", 0),
                },
            )
            n += 1
        return n

    def _load_invoices(self, company, rows) -> int:
        n = 0
        for r in rows:
            order = Order.objects.get(company=company, code=r["order_id"])
            Invoice.objects.update_or_create(
                company=company, code=r["invoice_id"],
                defaults={
                    "invoice_number": r["invoice_number"],
                    "order": order,
                    "invoice_date": r["invoice_date"],
                    "due_date": r.get("due_date"),
                    "total_amount": r.get("total_amount"),
                    "status": r.get("status_id", "draft"),
                    "paid_amount": r.get("paid_amount", 0),
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
        """Публикует событие по клиентам и заказам — для проверки workflow."""
        for customer in Customer.objects.filter(company=company):
            EventBus.publish(
                SE.CUSTOMER_SAVE,
                company_id=company.id,
                payload={
                    "customer_id": customer.id,
                    "code": customer.code,
                    "counterparty_id": customer.counterparty_id,
                },
            )
        for order in Order.objects.filter(company=company):
            EventBus.publish(
                SE.ORDER_CREATE,
                company_id=company.id,
                payload={
                    "order_id": order.id,
                    "customer_id": order.customer_id,
                },
            )


def _parse_int_id(value) -> int | None:
    """'EMP-010' → 10; 'MAT-006' → 6; 'CUR-001' → 1; 'ADDR-002' → 2."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        for prefix in ("EMP-", "MAT-", "CUR-", "ADDR-", "UNIT-", "POS-", "NP-", "DOC-"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None