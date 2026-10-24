"""
Демо-команда: загружает Procurement_test_data.json.

Использование:
    python manage.py demo_procurement --company=1
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import ProcurementEvents as PE

from apps.cp.models import Counterparty
from apps.procurement.models import (
    Delivery, Order, OrderHistory, OrderLine, Requisition,
    RequisitionLine, RFQ, RFQSupplier, Supplier, SupplierQuote,
)
from apps.wms.models import Material


class Command(BaseCommand):
    help = "Загружает тестовые данные Procurement"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/procurement/workflow/Procurement_test_data.json",
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
            # Порядок: поставщики → заявки → RFQ → заказы
            counters["supplier"] = self._load_suppliers(
                company, tables.get("procurement_supplier", []),
            )
            counters["requisition"] = self._load_requisitions(
                company, tables.get("procurement_requisition", []),
            )
            counters["requisition_line"] = self._load_requisition_lines(
                company, tables.get("procurement_requisition_line", []),
            )
            counters["rfq"] = self._load_rfqs(
                company, tables.get("procurement_rfq", []),
            )
            counters["rfq_supplier"] = self._load_rfq_suppliers(
                company, tables.get("procurement_rfq_supplier", []),
            )
            counters["supplier_quote"] = self._load_supplier_quotes(
                company, tables.get("procurement_supplier_quote", []),
            )
            counters["order"] = self._load_orders(
                company, tables.get("procurement_order", []),
            )
            counters["order_line"] = self._load_order_lines(
                company, tables.get("procurement_order_line", []),
            )
            counters["delivery"] = self._load_deliveries(
                company, tables.get("procurement_delivery", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные Procurement загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # ----------------------------------------------------------
    # Загрузчики
    # ----------------------------------------------------------

    def _load_suppliers(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp_id = self._resolve_cp(r.get("counterparty_id"), company)
            Supplier.objects.update_or_create(
                company=company, code=r["supplier_id"],
                defaults={
                    "counterparty_id": cp_id or 0,
                    "rating": r.get("rating"),
                    "payment_terms": r.get("payment_terms", ""),
                    "delivery_terms": r.get("delivery_terms", ""),
                    "lead_time_days": r.get("lead_time_days"),
                    "is_preferred": r.get("is_preferred", False),
                },
            )
            n += 1
        return n

    def _load_requisitions(self, company, rows) -> int:
        n = 0
        for r in rows:
            Requisition.objects.update_or_create(
                company=company, code=r["requisition_id"],
                defaults={
                    "requisition_number": r["requisition_number"],
                    "source_type": r.get("source_type", "manual"),
                    "source_id": _parse_int_id(r.get("source_id")),
                    "requisition_date": r["requisition_date"],
                    "requested_by_employee_id": _parse_emp_id(
                        r.get("requested_by_employee_id")
                    ),
                    "status": r.get("status_id", "draft"),
                    "planned_order_date": r.get("planned_order_date"),
                    "required_date": r.get("required_date"),
                },
            )
            n += 1
        return n

    def _load_requisition_lines(self, company, rows) -> int:
        n = 0
        for r in rows:
            req = Requisition.objects.get(
                company=company, code=r["requisition_id"],
            )
            RequisitionLine.objects.update_or_create(
                company=company, code=r["requisition_line_id"],
                defaults={
                    "requisition": req,
                    "material_id": self._resolve_material(r.get("material_id"), company) or 0,
                    "quantity": r["quantity"],
                    "unit_id": _parse_int_id(r.get("unit_id")),
                    "estimated_unit_cost": r.get("estimated_unit_cost"),
                },
            )
            n += 1
        return n

    def _load_rfqs(self, company, rows) -> int:
        n = 0
        for r in rows:
            req = (
                Requisition.objects.filter(
                    company=company, code=r["requisition_id"],
                ).first()
                if r.get("requisition_id") else None
            )
            RFQ.objects.update_or_create(
                company=company, code=r["rfq_id"],
                defaults={
                    "rfq_number": r["rfq_number"],
                    "requisition": req,
                    "rfq_date": r["rfq_date"],
                    "response_deadline": r.get("response_deadline"),
                    "status": r.get("status_id", "draft"),
                },
            )
            n += 1
        return n

    def _load_rfq_suppliers(self, company, rows) -> int:
        n = 0
        for r in rows:
            rfq = RFQ.objects.get(company=company, code=r["rfq_id"])
            sup = Supplier.objects.get(company=company, code=r["supplier_id"])
            RFQSupplier.objects.update_or_create(
                company=company, code=r["rfq_supplier_id"],
                defaults={"rfq": rfq, "supplier": sup},
            )
            n += 1
        return n

    def _load_supplier_quotes(self, company, rows) -> int:
        n = 0
        for r in rows:
            rfs = RFQSupplier.objects.get(
                company=company, code=r["rfq_supplier_id"],
            )
            SupplierQuote.objects.update_or_create(
                company=company, code=r["quote_id"],
                defaults={
                    "rfq_supplier": rfs,
                    "material_id": self._resolve_material(r.get("material_id"), company) or 0,
                    "unit_price": r["unit_price"],
                    "quantity": r["quantity"],
                    "delivery_days": r.get("delivery_days"),
                },
            )
            n += 1
        return n

    def _load_orders(self, company, rows) -> int:
        n = 0
        for r in rows:
            sup = Supplier.objects.get(company=company, code=r["supplier_id"])
            req = (
                Requisition.objects.filter(
                    company=company, code=r["requisition_id"],
                ).first()
                if r.get("requisition_id") else None
            )
            rfq = (
                RFQ.objects.filter(
                    company=company, code=r["rfq_id"],
                ).first()
                if r.get("rfq_id") else None
            )
            Order.objects.update_or_create(
                company=company, code=r["order_id"],
                defaults={
                    "order_number": r["order_number"],
                    "supplier": sup,
                    "requisition": req,
                    "rfq": rfq,
                    "order_date": r["order_date"],
                    "expected_delivery_date": r.get("expected_delivery_date"),
                    "actual_delivery_date": r.get("actual_delivery_date"),
                    "status": r.get("status_id", "draft"),
                    "total_amount": r.get("total_amount"),
                    "currency_id": _parse_int_id(r.get("currency_id")),
                    "created_by_employee_id": _parse_emp_id(
                        r.get("created_by_employee_id")
                    ),
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
                    "material_id": self._resolve_material(r.get("material_id"), company) or 0,
                    "quantity": r["quantity"],
                    "unit_price": r["unit_price"],
                    "total_price": r.get("total_price"),
                    "received_quantity": r.get("received_quantity", 0),
                },
            )
            n += 1
        return n

    def _load_deliveries(self, company, rows) -> int:
        n = 0
        for r in rows:
            order = Order.objects.get(company=company, code=r["order_id"])
            Delivery.objects.update_or_create(
                company=company, code=r["delivery_id"],
                defaults={
                    "order": order,
                    "delivery_date": r["delivery_date"],
                    "quantity": r["quantity"],
                    "status": r.get("status_id", "received"),
                },
            )
            n += 1
        return n

    # ----------------------------------------------------------
    # Утилиты
    # ----------------------------------------------------------

    def _resolve_cp(self, code: str | None, company) -> int | None:
        if not code:
            return None
        cp = Counterparty.objects.filter(company=company, code=code).first()
        return cp.id if cp else None

    def _resolve_material(self, code: str | None, company) -> int | None:
        """'MAT-001' → Material.id."""
        if not code:
            return None
        m = Material.objects.filter(company=company, code=code).first()
        return m.id if m else None

    def _emit_events(self, company) -> None:
        for order in Order.objects.filter(company=company, status="confirmed"):
            EventBus.publish(
                PE.ORDER_CONFIRM,
                company_id=company.id,
                payload={
                    "order_id": order.id,
                    "supplier_id": order.supplier_id,
                    "total_amount": float(order.total_amount) if order.total_amount else None,
                    "currency_id": order.currency_id,
                    "order_date": order.order_date.isoformat(),
                },
            )


def _parse_int_id(value) -> int | None:
    """'UNIT-001' → 1; 'MAT-001' → 1; 'CUR-001' → 1."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        for prefix in ("EMP-", "MAT-", "CUR-", "ADDR-", "BANK-", "UNIT-",
                       "POS-", "NP-", "DOC-", "PROD-", "REQ-", "RFQ-", "PO-"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None


def _parse_emp_id(value) -> int | None:
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        if s.startswith("EMP-"):
            s = s[len("EMP-"):]
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None