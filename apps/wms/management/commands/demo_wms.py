"""
Демо-команда: загружает WMS_test_data.json.

Использование:
    python manage.py demo_wms --company=1
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import WMSEvents as WE

from apps.cp.models import Counterparty
from apps.wms.models import (
    Container, ContainerItem, ContainerType, GoodsReceipt,
    GoodsReceiptLine, Inventory, Material, MaterialGroup, MaterialLot,
    SerialNumber, StorageLocation, Warehouse, WarehouseType,
)


class Command(BaseCommand):
    help = "Загружает тестовые данные WMS"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/wms/workflow/WMS_test_data.json",
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
            counters["warehouse_type"] = self._load_warehouse_types(
                company, tables.get("wms_warehouse_type", []),
            )
            counters["warehouse"] = self._load_warehouses(
                company, tables.get("wms_warehouse", []),
            )
            counters["storage_location"] = self._load_storage_locations(
                company, tables.get("wms_storage_location", []),
            )
            counters["material_group"] = self._load_material_groups(
                company, tables.get("wms_material_group", []),
            )
            counters["material"] = self._load_materials(
                company, tables.get("wms_material", []),
            )
            counters["material_lot"] = self._load_material_lots(
                company, tables.get("wms_material_lot", []),
            )
            counters["inventory"] = self._load_inventory(
                company, tables.get("wms_inventory", []),
            )
            counters["goods_receipt"] = self._load_goods_receipts(
                company, tables.get("wms_goods_receipt", []),
            )
            counters["goods_receipt_line"] = self._load_goods_receipt_lines(
                company, tables.get("wms_goods_receipt_line", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные WMS загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # --------------------------------------------------------------
    # Загрузчики
    # --------------------------------------------------------------

    def _load_warehouse_types(self, company, rows) -> int:
        n = 0
        for r in rows:
            WarehouseType.objects.update_or_create(
                company=company, code=r["warehouse_type_id"],
                defaults={"name": r["warehouse_type_name"]},
            )
            n += 1
        return n

    def _load_warehouses(self, company, rows) -> int:
        n = 0
        for r in rows:
            wt = (
                WarehouseType.objects.filter(
                    company=company, code=r["warehouse_type_id"],
                ).first()
                if r.get("warehouse_type_id") else None
            )
            Warehouse.objects.update_or_create(
                company=company, code=r["warehouse_id"],
                defaults={
                    "name": r["warehouse_name"],
                    "warehouse_type": wt,
                    "address_id": _parse_int_id(r.get("address_id")),
                },
            )
            n += 1
        return n

    def _load_storage_locations(self, company, rows) -> int:
        n = 0
        for r in rows:
            wh = Warehouse.objects.get(company=company, code=r["warehouse_id"])
            StorageLocation.objects.update_or_create(
                company=company, code=r["location_id"],
                defaults={
                    "warehouse": wh,
                    "location_code": r["location_code"],
                    "location_type": r.get("location_type", ""),
                },
            )
            n += 1
        return n

    def _load_material_groups(self, company, rows) -> int:
        n = 0
        objs = {}
        # Первый проход: без parent
        for r in rows:
            mg, _ = MaterialGroup.objects.update_or_create(
                company=company, code=r["material_group_id"],
                defaults={"name": r["material_group_name"]},
            )
            objs[r["material_group_id"]] = mg
            n += 1
        # Второй проход: parent
        for r in rows:
            if r.get("parent_id"):
                parent = objs.get(r["parent_id"])
                if parent:
                    objs[r["material_group_id"]].parent = parent
                    objs[r["material_group_id"]].save(update_fields=["parent"])
        return n

    def _load_materials(self, company, rows) -> int:
        n = 0
        for r in rows:
            grp = (
                MaterialGroup.objects.filter(
                    company=company, code=r["material_group_id"],
                ).first()
                if r.get("material_group_id") else None
            )
            Material.objects.update_or_create(
                company=company, code=r["material_id"],
                defaults={
                    "material_group": grp,
                    "material_code": r["material_code"],
                    "name": r["material_name"],
                    "unit_id": _parse_int_id(r.get("unit_id")),
                    "barcode": r.get("barcode", ""),
                    "min_stock_level": r.get("min_stock_level"),
                },
            )
            n += 1
        return n

    def _load_material_lots(self, company, rows) -> int:
        n = 0
        for r in rows:
            mat = Material.objects.get(company=company, code=r["material_id"])
            MaterialLot.objects.update_or_create(
                company=company, code=r["lot_id"],
                defaults={
                    "material": mat,
                    "lot_number": r["lot_number"],
                    "manufacture_date": r.get("manufacture_date"),
                    "expiration_date": r.get("expiration_date"),
                },
            )
            n += 1
        return n

    def _load_inventory(self, company, rows) -> int:
        n = 0
        for r in rows:
            mat = Material.objects.get(company=company, code=r["material_id"])
            loc = StorageLocation.objects.get(
                company=company, code=r["location_id"],
            )
            lot = (
                MaterialLot.objects.filter(
                    company=company, code=r["lot_id"],
                ).first()
                if r.get("lot_id") else None
            )
            Inventory.objects.update_or_create(
                company=company, code=r["inventory_id"],
                defaults={
                    "material": mat,
                    "location": loc,
                    "lot": lot,
                    "quantity": r["quantity"],
                    "unit_cost": r.get("unit_cost"),
                },
            )
            n += 1
        return n

    def _load_goods_receipts(self, company, rows) -> int:
        n = 0
        for r in rows:
            wh = Warehouse.objects.get(company=company, code=r["warehouse_id"])
            GoodsReceipt.objects.update_or_create(
                company=company, code=r["receipt_id"],
                defaults={
                    "warehouse": wh,
                    "counterparty_id": self._resolve_cp(r.get("counterparty_id"), company),
                    "receipt_date": r["receipt_date"],
                    "document_id": _parse_int_id(r.get("document_id")),
                    "status": r.get("status", "draft"),
                },
            )
            n += 1
        return n

    def _load_goods_receipt_lines(self, company, rows) -> int:
        n = 0
        for r in rows:
            gr = GoodsReceipt.objects.get(company=company, code=r["receipt_id"])
            mat = Material.objects.get(company=company, code=r["material_id"])
            lot = (
                MaterialLot.objects.filter(
                    company=company, code=r["lot_id"],
                ).first()
                if r.get("lot_id") else None
            )
            loc = (
                StorageLocation.objects.filter(
                    company=company, code=r["location_id"],
                ).first()
                if r.get("location_id") else None
            )
            GoodsReceiptLine.objects.update_or_create(
                company=company, code=r["receipt_line_id"],
                defaults={
                    "receipt": gr,
                    "material": mat,
                    "lot": lot,
                    "location": loc,
                    "quantity": r["quantity"],
                    "unit_cost": r.get("unit_cost"),
                },
            )
            n += 1
        return n

    # --------------------------------------------------------------
    # Утилиты
    # --------------------------------------------------------------

    def _resolve_cp(self, code: str | None, company) -> int | None:
        if not code:
            return None
        cp = Counterparty.objects.filter(company=company, code=code).first()
        return cp.id if cp else None

    def _emit_events(self, company) -> None:
        for m in Material.objects.filter(company=company):
            EventBus.publish(
                WE.MATERIAL_CREATE,
                company_id=company.id,
                payload={
                    "material_id": m.id,
                    "material_code": m.material_code,
                    "name": m.name,
                },
            )


def _parse_int_id(value) -> int | None:
    """'ADDR-001' → 1; 'UNIT-001' → 1; 'CP-001' → 1; None → None."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        for prefix in ("EMP-", "MAT-", "CUR-", "ADDR-", "BANK-", "UNIT-", "POS-", "NP-", "DOC-"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None