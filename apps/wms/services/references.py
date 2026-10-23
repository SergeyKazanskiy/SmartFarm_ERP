"""
Справочники WMS (OP-WMS-01…09, 31…37).
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import WMSEvents as WE

from apps.wms.models import (
    Container, ContainerItem, ContainerType, Material, MaterialGroup,
    MaterialLot, SerialNumber, StorageLocation, Warehouse, WarehouseType,
)
from apps.wms.services.helpers import gen_code


class WarehouseTypeService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        wt = WarehouseType.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("WT"),
            name=data["name"],
        )
        EventBus.publish(
            WE.WAREHOUSE_CREATE,
            company_id=company_id,
            payload={"warehouse_type_id": wt.id, "name": wt.name},
        )
        return wt


class WarehouseService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Warehouse | None = None):
        """OP-WMS-01 / OP-WMS-02."""
        if instance is None:
            instance = Warehouse(
                company_id=company_id,
                code=data.get("code") or gen_code("WH"),
            )
        for field in ("name", "warehouse_type_id", "address_id"):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        event = WE.WAREHOUSE_CREATE if instance._state.adding else WE.WAREHOUSE_UPDATE
        EventBus.publish(
            event,
            company_id=company_id,
            payload={"warehouse_id": instance.id, "name": instance.name},
        )
        return instance


class StorageLocationService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: StorageLocation | None = None):
        """OP-WMS-03 / OP-WMS-04."""
        if instance is None:
            instance = StorageLocation(
                company_id=company_id,
                code=data.get("code") or gen_code("LOC"),
            )
        for field in ("warehouse_id", "location_code", "location_type"):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()
        return instance


class MaterialGroupService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-05."""
        mg = MaterialGroup.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("MG"),
            name=data["name"],
            parent_id=data.get("parent_id"),
        )
        EventBus.publish(
            WE.MATERIAL_GROUP_CREATE,
            company_id=company_id,
            payload={"material_group_id": mg.id, "name": mg.name},
        )
        return mg

    @staticmethod
    @transaction.atomic
    def rename(*, company_id: int, group_id: int, new_name: str):
        """OP-WMS-06."""
        mg = MaterialGroup.objects.select_for_update().get(
            pk=group_id, company_id=company_id,
        )
        mg.name = new_name
        mg.save(update_fields=["name", "updated_at"])
        EventBus.publish(
            WE.MATERIAL_GROUP_RENAME,
            company_id=company_id,
            payload={"material_group_id": mg.id, "new_name": new_name},
        )
        return mg


class MaterialService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Material | None = None):
        """OP-WMS-07 / OP-WMS-08."""
        if instance is None:
            instance = Material(
                company_id=company_id,
                code=data.get("code") or gen_code("MAT"),
            )
        for field in (
            "material_group_id", "material_code", "name",
            "unit_id", "barcode", "min_stock_level",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        event = WE.MATERIAL_CREATE if instance._state.adding else WE.MATERIAL_UPDATE
        EventBus.publish(
            event,
            company_id=company_id,
            payload={
                "material_id": instance.id,
                "material_code": instance.material_code,
                "name": instance.name,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def update_reorder_point(*, company_id: int, material_id: int, min_stock_level):
        """OP-WMS-09."""
        m = Material.objects.select_for_update().get(
            pk=material_id, company_id=company_id,
        )
        m.min_stock_level = min_stock_level
        m.save(update_fields=["min_stock_level", "updated_at"])
        EventBus.publish(
            WE.MATERIAL_UPDATE_REORDER_POINT,
            company_id=company_id,
            payload={
                "material_id": m.id,
                "min_stock_level": float(m.min_stock_level) if m.min_stock_level else None,
            },
        )
        return m


class MaterialLotService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-31."""
        lot = MaterialLot.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("LOT"),
            material_id=data["material_id"],
            lot_number=data["lot_number"],
            manufacture_date=data.get("manufacture_date"),
            expiration_date=data.get("expiration_date"),
        )
        EventBus.publish(
            WE.MATERIAL_LOT_CREATE,
            company_id=company_id,
            payload={
                "lot_id": lot.id,
                "material_id": lot.material_id,
                "lot_number": lot.lot_number,
            },
        )
        return lot

    @staticmethod
    @transaction.atomic
    def update_expiration(*, company_id: int, lot_id: int, expiration_date):
        """OP-WMS-32."""
        lot = MaterialLot.objects.select_for_update().get(
            pk=lot_id, company_id=company_id,
        )
        lot.expiration_date = expiration_date
        lot.save(update_fields=["expiration_date", "updated_at"])
        EventBus.publish(
            WE.MATERIAL_LOT_UPDATE_EXPIRATION,
            company_id=company_id,
            payload={"lot_id": lot.id},
        )
        return lot


class SerialNumberService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-33."""
        sn = SerialNumber.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SN"),
            material_id=data["material_id"],
            serial_number=data["serial_number"],
        )
        EventBus.publish(
            WE.SERIAL_NUMBER_CREATE,
            company_id=company_id,
            payload={"serial_id": sn.id, "material_id": sn.material_id},
        )
        return sn


class ContainerTypeService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-34."""
        ct = ContainerType.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("CT"),
            name=data["name"],
        )
        EventBus.publish(
            WE.CONTAINER_TYPE_CREATE,
            company_id=company_id,
            payload={"container_type_id": ct.id, "name": ct.name},
        )
        return ct


class ContainerService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-35."""
        c = Container.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("CONT"),
            container_type_id=data.get("container_type_id"),
            container_code=data["container_code"],
        )
        EventBus.publish(
            WE.CONTAINER_CREATE,
            company_id=company_id,
            payload={"container_id": c.id, "container_code": c.container_code},
        )
        return c


class ContainerItemService:

    @staticmethod
    @transaction.atomic
    def add(*, company_id: int, data: dict):
        """OP-WMS-36."""
        ci = ContainerItem.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("CI"),
            container_id=data["container_id"],
            inventory_id=data["inventory_id"],
        )
        EventBus.publish(
            WE.CONTAINER_ITEM_ADD,
            company_id=company_id,
            payload={"container_item_id": ci.id, "container_id": ci.container_id},
        )
        return ci

    @staticmethod
    @transaction.atomic
    def remove(*, company_id: int, container_item_id: int):
        """OP-WMS-37."""
        ci = ContainerItem.objects.get(pk=container_item_id, company_id=company_id)
        payload = {"container_item_id": ci.id, "container_id": ci.container_id}
        ci.delete()
        EventBus.publish(
            WE.CONTAINER_ITEM_REMOVE,
            company_id=company_id, payload=payload,
        )