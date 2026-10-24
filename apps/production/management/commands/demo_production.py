"""
Демо-команда: загружает Production_test_data.json.

Использование:
    python manage.py demo_production --company=1
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import ProductionEvents as PRE

from apps.production.models import (
    Bom, BomItem, MaterialPriceHistory, OperationDefinition,
    OperationExecution, ProductionOrder, QualityPoint,
    Routing, Technology, WorkCenter, WorkOrder,
)
from apps.wms.models import Material


class Command(BaseCommand):
    help = "Загружает тестовые данные Production"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/production/workflow/Production_test_data.json",
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
            # Мастер-данные
            counters["technology"] = self._load_technologies(
                company, tables.get("prod_technology", []),
            )
            counters["work_center"] = self._load_work_centers(
                company, tables.get("prod_work_center", []),
            )
            counters["routing"] = self._load_routings(
                company, tables.get("prod_routing", []),
            )
            counters["operation_definition"] = self._load_operations(
                company, tables.get("prod_operation_definition", []),
            )
            counters["quality_point"] = self._load_quality_points(
                company, tables.get("prod_quality_point", []),
            )
            counters["bom"] = self._load_boms(
                company, tables.get("prod_bom", []),
            )
            counters["bom_item"] = self._load_bom_items(
                company, tables.get("prod_bom_item", []),
            )
            # Исполнительный цикл
            counters["production_order"] = self._load_production_orders(
                company, tables.get("prod_production_order", []),
            )
            counters["work_order"] = self._load_work_orders(
                company, tables.get("prod_work_order", []),
            )
            counters["operation_execution"] = self._load_executions(
                company, tables.get("prod_operation_execution", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные Production загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # ----------------------------------------------------------
    # Загрузчики
    # ----------------------------------------------------------

    def _load_technologies(self, company, rows) -> int:
        n = 0
        for r in rows:
            Technology.objects.update_or_create(
                company=company, code=r["technology_id"],
                defaults={"name": r["technology_name"]},
            )
            n += 1
        return n

    def _load_work_centers(self, company, rows) -> int:
        n = 0
        for r in rows:
            WorkCenter.objects.update_or_create(
                company=company, code=r["work_center_id"],
                defaults={"name": r["work_center_name"]},
            )
            n += 1
        return n

    def _load_routings(self, company, rows) -> int:
        n = 0
        for r in rows:
            tech = (
                Technology.objects.filter(
                    company=company, code=r["technology_id"],
                ).first()
                if r.get("technology_id") else None
            )
            Routing.objects.update_or_create(
                company=company, code=r["routing_id"],
                defaults={
                    "technology": tech,
                    "name": r["routing_name"],
                },
            )
            n += 1
        return n

    def _load_operations(self, company, rows) -> int:
        n = 0
        for r in rows:
            routing = Routing.objects.get(
                company=company, code=r["routing_id"],
            )
            wc = (
                WorkCenter.objects.filter(
                    company=company, code=r["work_center_id"],
                ).first()
                if r.get("work_center_id") else None
            )
            OperationDefinition.objects.update_or_create(
                company=company, code=r["operation_id"],
                defaults={
                    "routing": routing,
                    "name": r["operation_name"],
                    "sequence_no": r["sequence_no"],
                    "work_center": wc,
                    "resources_json": r.get("resources_json") or [],
                    "parameters_json": r.get("parameters_json") or [],
                },
            )
            n += 1
        return n

    def _load_quality_points(self, company, rows) -> int:
        n = 0
        for r in rows:
            op = OperationDefinition.objects.get(
                company=company, code=r["operation_id"],
            )
            QualityPoint.objects.update_or_create(
                company=company, code=r["quality_point_id"],
                defaults={
                    "operation": op,
                    "name": r["quality_point_name"],
                },
            )
            n += 1
        return n

    def _load_boms(self, company, rows) -> int:
        n = 0
        for r in rows:
            Bom.objects.update_or_create(
                company=company, code=r["bom_id"],
                defaults={
                    "product_material_id": self._resolve_material(
                        r.get("product_material_id"), company,
                    ) or 0,
                    "name": r["bom_name"],
                },
            )
            n += 1
        return n

    def _load_bom_items(self, company, rows) -> int:
        n = 0
        for r in rows:
            bom = Bom.objects.get(company=company, code=r["bom_id"])
            BomItem.objects.update_or_create(
                company=company, code=r["bom_item_id"],
                defaults={
                    "bom": bom,
                    "material_id": self._resolve_material(
                        r.get("material_id"), company,
                    ) or 0,
                    "quantity": r["quantity"],
                    "unit_cost": r.get("unit_cost"),
                },
            )
            n += 1
        return n

    def _load_production_orders(self, company, rows) -> int:
        n = 0
        for r in rows:
            bom = (
                Bom.objects.filter(
                    company=company, code=r["bom_id"],
                ).first()
                if r.get("bom_id") else None
            )
            routing = (
                Routing.objects.filter(
                    company=company, code=r["routing_id"],
                ).first()
                if r.get("routing_id") else None
            )
            ProductionOrder.objects.update_or_create(
                company=company, code=r["production_order_id"],
                defaults={
                    "bom": bom,
                    "routing": routing,
                    "planned_quantity": r["planned_quantity"],
                    "planned_start_date": r.get("planned_start_date"),
                    "planned_end_date": r.get("planned_end_date"),
                    "status": r.get("status_id", "draft"),
                },
            )
            n += 1
        return n

    def _load_work_orders(self, company, rows) -> int:
        n = 0
        for r in rows:
            po = ProductionOrder.objects.get(
                company=company, code=r["production_order_id"],
            )
            WorkOrder.objects.update_or_create(
                company=company, code=r["work_order_id"],
                defaults={
                    "production_order": po,
                    "status": r.get("status_id", "planned"),
                    "planned_start": r.get("planned_start"),
                    "planned_finish": r.get("planned_finish"),
                    "actual_start": r.get("actual_start"),
                    "actual_finish": r.get("actual_finish"),
                    "actual_materials_json": r.get("actual_materials_json") or [],
                },
            )
            n += 1
        return n

    def _load_executions(self, company, rows) -> int:
        n = 0
        for r in rows:
            wo = WorkOrder.objects.get(
                company=company, code=r["work_order_id"],
            )
            op = OperationDefinition.objects.get(
                company=company, code=r["operation_id"],
            )
            wc = (
                WorkCenter.objects.filter(
                    company=company, code=r["work_center_id"],
                ).first()
                if r.get("work_center_id") else None
            )
            OperationExecution.objects.update_or_create(
                company=company, code=r["execution_id"],
                defaults={
                    "work_order": wo,
                    "operation": op,
                    "work_center": wc,
                    "performed_by_employee_id": _parse_emp_id(
                        r.get("performed_by_employee_id")
                    ),
                    "start_time": r.get("start_time"),
                    "end_time": r.get("end_time"),
                    "status": r.get("status_id", "in_progress"),
                    "measurements_json": r.get("measurements_json") or [],
                    "quality_results_json": r.get("quality_results_json") or [],
                },
            )
            n += 1
        return n

    # ----------------------------------------------------------
    # Утилиты
    # ----------------------------------------------------------

    def _resolve_material(self, code: str | None, company) -> int | None:
        """'MAT-006' → Material.id."""
        if not code:
            return None
        m = Material.objects.filter(company=company, code=code).first()
        return m.id if m else None

    def _emit_events(self, company) -> None:
        for order in ProductionOrder.objects.filter(company=company, status="confirmed"):
            EventBus.publish(
                PRE.PRODUCTION_ORDER_CONFIRM,
                company_id=company.id,
                payload={
                    "production_order_id": order.id,
                    "bom_id": order.bom_id,
                    "planned_quantity": float(order.planned_quantity),
                },
            )


def _parse_emp_id(value) -> int | None:
    """'EMP-007' → 7; 'MAT-006' → 6; None → None."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        for prefix in ("EMP-", "MAT-", "CUR-", "ADDR-", "UNIT-",
                       "POS-", "NP-", "DOC-", "WC-", "TECH-", "ROUT-"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None