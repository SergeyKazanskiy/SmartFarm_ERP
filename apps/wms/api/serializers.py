"""
DRF-сериализаторы WMS.
"""
from rest_framework import serializers

from apps.wms.models import (
    Container, ContainerItem, ContainerType, GoodsReceipt, GoodsReceiptLine,
    Inventory, InventorySnapshot, InventorySnapshotItem, InventoryTransaction,
    Material, MaterialGroup, MaterialLot, MaterialReservation, SerialNumber,
    StorageLocation, Transfer, TransferLine, Warehouse, WarehouseType,
    WriteOff, WriteOffLine,
)


class WarehouseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseType
        fields = ["id", "code", "name"]


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ["id", "code", "name", "warehouse_type", "address_id"]


class StorageLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageLocation
        fields = ["id", "code", "warehouse", "location_code", "location_type"]


class MaterialGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialGroup
        fields = ["id", "code", "name", "parent"]


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = [
            "id", "code", "material_group", "material_code", "name",
            "unit_id", "barcode", "min_stock_level",
        ]


class MaterialLotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialLot
        fields = [
            "id", "code", "material", "lot_number",
            "manufacture_date", "expiration_date",
        ]


class SerialNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = SerialNumber
        fields = ["id", "code", "material", "serial_number"]


class InventorySerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source="material.name", read_only=True)
    location_code = serializers.CharField(
        source="location.location_code", read_only=True,
    )

    class Meta:
        model = Inventory
        fields = [
            "id", "code", "material", "material_name",
            "location", "location_code", "lot", "serial",
            "quantity", "unit_cost",
        ]
        read_only_fields = ["unit_cost"]


class InventoryTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryTransaction
        fields = [
            "id", "code", "inventory", "transaction_type", "quantity",
            "source_document_type", "source_document_id",
            "reservation", "task_id", "transaction_date",
        ]
        read_only_fields = fields


class MaterialReservationSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = MaterialReservation
        fields = [
            "id", "code", "material", "warehouse", "quantity", "status",
            "status_display", "task_object_type", "task_object_id",
            "reserved_at", "issued_at", "released_at",
        ]
        read_only_fields = ["status", "reserved_at", "issued_at", "released_at"]


class GoodsReceiptLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceiptLine
        fields = [
            "id", "code", "receipt", "material", "lot", "location",
            "quantity", "unit_cost",
        ]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lines = GoodsReceiptLineSerializer(many=True, read_only=True)

    class Meta:
        model = GoodsReceipt
        fields = [
            "id", "code", "warehouse", "counterparty_id", "receipt_date",
            "document_id", "status", "status_display", "posted_at", "lines",
        ]
        read_only_fields = ["status", "posted_at"]


class TransferLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferLine
        fields = ["id", "code", "transfer", "material", "quantity"]


class TransferSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lines = TransferLineSerializer(many=True, read_only=True)

    class Meta:
        model = Transfer
        fields = [
            "id", "code", "from_warehouse", "to_warehouse",
            "transfer_date", "status", "status_display", "posted_at", "lines",
        ]
        read_only_fields = ["status", "posted_at"]


class WriteOffLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = WriteOffLine
        fields = ["id", "code", "writeoff", "material", "quantity"]


class WriteOffSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    lines = WriteOffLineSerializer(many=True, read_only=True)

    class Meta:
        model = WriteOff
        fields = [
            "id", "code", "warehouse", "writeoff_date", "reason",
            "status", "status_display", "posted_at", "lines",
        ]
        read_only_fields = ["status", "posted_at"]


class InventorySnapshotItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventorySnapshotItem
        fields = ["id", "code", "snapshot", "inventory", "quantity", "counted_quantity"]
        read_only_fields = ["quantity"]


class InventorySnapshotSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    items = InventorySnapshotItemSerializer(many=True, read_only=True)

    class Meta:
        model = InventorySnapshot
        fields = [
            "id", "code", "warehouse", "snapshot_date",
            "status", "status_display", "items",
        ]
        read_only_fields = ["status", "snapshot_date"]


class ContainerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContainerType
        fields = ["id", "code", "name"]


class ContainerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Container
        fields = ["id", "code", "container_type", "container_code"]


class ContainerItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContainerItem
        fields = ["id", "code", "container", "inventory"]