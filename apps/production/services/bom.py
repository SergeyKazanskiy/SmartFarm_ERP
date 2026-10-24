"""
Спецификация (BOM) — OP-PROD-15…19, OP-PROD-43.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus
from core.events import ProductionEvents as PRE

from apps.production.models import Bom, BomItem, MaterialPriceHistory
from apps.production.services.helpers import gen_code


class BomService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-15."""
        bom = Bom.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("BOM"),
            product_material_id=data["product_material_id"],
            name=data["name"],
        )
        EventBus.publish(
            PRE.BOM_CREATE,
            company_id=company_id,
            payload={
                "bom_id": bom.id,
                "product_material_id": bom.product_material_id,
            },
        )
        return bom

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, bom_id: int, data: dict):
        """OP-PROD-16."""
        bom = Bom.objects.select_for_update().get(
            pk=bom_id, company_id=company_id,
        )
        for field in ("name", "product_material_id"):
            if field in data:
                setattr(bom, field, data[field])
        bom.save()
        EventBus.publish(
            PRE.BOM_UPDATE,
            company_id=company_id,
            payload={"bom_id": bom.id},
        )
        return bom


class BomItemService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-17."""
        item = BomItem.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("BOMI"),
            bom_id=data["bom_id"],
            material_id=data["material_id"],
            quantity=data["quantity"],
            unit_cost=data.get("unit_cost"),
        )
        EventBus.publish(
            PRE.BOM_ITEM_CREATE,
            company_id=company_id,
            payload={
                "bom_item_id": item.id,
                "bom_id": item.bom_id,
                "material_id": item.material_id,
            },
        )
        return item

    @staticmethod
    @transaction.atomic
    def update_quantity(*, company_id: int, bom_item_id: int, quantity):
        """OP-PROD-18."""
        item = BomItem.objects.select_for_update().get(
            pk=bom_item_id, company_id=company_id,
        )
        item.quantity = quantity
        item.save(update_fields=["quantity", "updated_at"])
        EventBus.publish(
            PRE.BOM_ITEM_UPDATE_QUANTITY,
            company_id=company_id,
            payload={"bom_item_id": item.id},
        )
        return item

    @staticmethod
    @transaction.atomic
    def replace_material(*, company_id: int, bom_item_id: int, material_id: int):
        """OP-PROD-19."""
        item = BomItem.objects.select_for_update().get(
            pk=bom_item_id, company_id=company_id,
        )
        item.material_id = material_id
        item.save(update_fields=["material_id", "updated_at"])
        EventBus.publish(
            PRE.BOM_ITEM_REPLACE_MATERIAL,
            company_id=company_id,
            payload={"bom_item_id": item.id, "material_id": material_id},
        )
        return item

    @staticmethod
    @transaction.atomic
    def update_cost(*, company_id: int, bom_item_id: int, unit_cost,
                    actor_employee_id: int | None = None):
        """OP-PROD-43 + запись в MaterialPriceHistory."""
        item = BomItem.objects.select_for_update().get(
            pk=bom_item_id, company_id=company_id,
        )
        item.unit_cost = unit_cost
        item.save(update_fields=["unit_cost", "updated_at"])

        MaterialPriceHistory.objects.create(
            company_id=company_id,
            code=gen_code("MPH"),
            material_id=item.material_id,
            unit_cost=unit_cost,
            effective_date=timezone.now().date(),
            created_by_employee_id=actor_employee_id,
        )
        EventBus.publish(
            PRE.BOM_ITEM_UPDATE_COST,
            company_id=company_id,
            payload={"bom_item_id": item.id, "unit_cost": float(unit_cost)},
        )
        return item


class MaterialPriceHistoryService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict,
               actor_employee_id: int | None = None):
        return MaterialPriceHistory.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("MPH"),
            material_id=data["material_id"],
            unit_cost=data["unit_cost"],
            effective_date=data["effective_date"],
            created_by_employee_id=actor_employee_id,
        )