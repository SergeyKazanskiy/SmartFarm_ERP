"""
DRF ViewSets WMS.
"""
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.wms.api.serializers import (
    ContainerItemSerializer, ContainerSerializer, ContainerTypeSerializer,
    GoodsReceiptLineSerializer, GoodsReceiptSerializer,
    InventorySerializer, InventorySnapshotItemSerializer,
    InventorySnapshotSerializer, InventoryTransactionSerializer,
    MaterialGroupSerializer, MaterialLotSerializer,
    MaterialReservationSerializer, MaterialSerializer,
    SerialNumberSerializer, StorageLocationSerializer,
    TransferLineSerializer, TransferSerializer,
    WarehouseSerializer, WarehouseTypeSerializer,
    WriteOffLineSerializer, WriteOffSerializer,
)
from apps.wms.models import (
    Container, ContainerItem, ContainerType, GoodsReceipt, GoodsReceiptLine,
    Inventory, InventorySnapshot, InventorySnapshotItem, InventoryTransaction,
    Material, MaterialGroup, MaterialLot, MaterialReservation, SerialNumber,
    StorageLocation, Transfer, TransferLine, Warehouse, WarehouseType,
    WriteOff, WriteOffLine,
)
from apps.wms.services import (
    ContainerItemService, ContainerService, ContainerTypeService,
    GoodsReceiptLineService, GoodsReceiptService,
    InventorySnapshotItemService, InventorySnapshotService,
    MaterialGroupService, MaterialLotService, MaterialReservationService,
    MaterialService, SerialNumberService, StorageLocationService,
    TransferLineService, TransferService,
    WarehouseService, WarehouseTypeService,
    WriteOffLineService, WriteOffService,
)


class CompanyScopedMixin:
    def get_company_id(self) -> int:
        cid = getattr(self.request.user, "current_company_id", None)
        if not cid:
            raise PermissionDenied("Компания не выбрана")
        return cid


# --- Справочники ---

class WarehouseTypeViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WarehouseTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WarehouseType.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = WarehouseTypeService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class WarehouseViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Warehouse.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = WarehouseService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = WarehouseService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


class StorageLocationViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = StorageLocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = StorageLocation.objects.filter(company_id=self.get_company_id())
        wh = self.request.query_params.get("warehouse_id")
        if wh:
            qs = qs.filter(warehouse_id=wh)
        return qs

    def perform_create(self, serializer):
        serializer.instance = StorageLocationService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = StorageLocationService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )


class MaterialGroupViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = MaterialGroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MaterialGroup.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = MaterialGroupService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class MaterialViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = MaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Material.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            grp = self.request.query_params.get("material_group_id")
            if grp:
                qs = qs.filter(material_group_id=grp)
            search = self.request.query_params.get("search")
            if search:
                from django.db.models import Q
                qs = qs.filter(
                    Q(material_code__icontains=search) | Q(name__icontains=search)
                )
        return qs

    def perform_create(self, serializer):
        serializer.instance = MaterialService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = MaterialService.save(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
            instance=serializer.instance,
        )

    @action(detail=True, methods=["post"], url_path="update-reorder-point")
    def update_reorder_point(self, request, pk=None):
        m = self.get_object()
        val = request.data.get("min_stock_level")
        if val is None:
            raise ValidationError("min_stock_level обязателен")
        m = MaterialService.update_reorder_point(
            company_id=self.get_company_id(),
            material_id=m.id, min_stock_level=val,
        )
        return Response(MaterialSerializer(m).data)


class MaterialLotViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = MaterialLotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MaterialLot.objects.filter(company_id=self.get_company_id())
        m = self.request.query_params.get("material_id")
        if m:
            qs = qs.filter(material_id=m)
        return qs.order_by("-expiration_date")

    def perform_create(self, serializer):
        serializer.instance = MaterialLotService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class SerialNumberViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = SerialNumberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SerialNumber.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = SerialNumberService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# --- Остатки ---

class InventoryViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Inventory.objects.filter(
            company_id=self.get_company_id(),
        ).select_related("material", "location")
        if self.action == "list":
            m = self.request.query_params.get("material_id")
            if m:
                qs = qs.filter(material_id=m)
            loc = self.request.query_params.get("location_id")
            if loc:
                qs = qs.filter(location_id=loc)
            wh = self.request.query_params.get("warehouse_id")
            if wh:
                qs = qs.filter(location__warehouse_id=wh)
        return qs


class InventoryTransactionViewSet(
    CompanyScopedMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = InventoryTransaction.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            tp = self.request.query_params.get("transaction_type")
            if tp:
                qs = qs.filter(transaction_type=tp)
            inv = self.request.query_params.get("inventory_id")
            if inv:
                qs = qs.filter(inventory_id=inv)
        return qs.order_by("-transaction_date")


# --- Приход ---

class GoodsReceiptViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = GoodsReceiptSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = GoodsReceipt.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-receipt_date")

    def perform_create(self, serializer):
        serializer.instance = GoodsReceiptService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        gr = self.get_object()
        try:
            gr = GoodsReceiptService.post(
                company_id=self.get_company_id(), receipt_id=gr.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(GoodsReceiptSerializer(gr).data)

    @action(detail=True, methods=["post"])
    def unpost(self, request, pk=None):
        gr = self.get_object()
        try:
            gr = GoodsReceiptService.unpost(
                company_id=self.get_company_id(), receipt_id=gr.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(GoodsReceiptSerializer(gr).data)


class GoodsReceiptLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = GoodsReceiptLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = GoodsReceiptLine.objects.filter(company_id=self.get_company_id())
        r = self.request.query_params.get("receipt_id")
        if r:
            qs = qs.filter(receipt_id=r)
        return qs

    def perform_create(self, serializer):
        serializer.instance = GoodsReceiptLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = GoodsReceiptLineService.update(
            company_id=self.get_company_id(),
            line_id=serializer.instance.id,
            data=dict(serializer.validated_data),
        )


# --- Резервирование ---

class MaterialReservationViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = MaterialReservationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = MaterialReservation.objects.filter(company_id=self.get_company_id())
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-reserved_at")

    def perform_create(self, serializer):
        serializer.instance = MaterialReservationService.reserve(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        r = self.get_object()
        try:
            r = MaterialReservationService.issue(
                company_id=self.get_company_id(), reservation_id=r.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(MaterialReservationSerializer(r).data)

    @action(detail=True, methods=["post"])
    def release(self, request, pk=None):
        r = self.get_object()
        try:
            r = MaterialReservationService.release(
                company_id=self.get_company_id(), reservation_id=r.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(MaterialReservationSerializer(r).data)


# --- Перемещение ---

class TransferViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = TransferSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Transfer.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-transfer_date")

    def perform_create(self, serializer):
        serializer.instance = TransferService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        t = self.get_object()
        try:
            t = TransferService.post(
                company_id=self.get_company_id(), transfer_id=t.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(TransferSerializer(t).data)

    @action(detail=True, methods=["post"])
    def unpost(self, request, pk=None):
        t = self.get_object()
        try:
            t = TransferService.unpost(
                company_id=self.get_company_id(), transfer_id=t.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(TransferSerializer(t).data)


class TransferLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = TransferLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = TransferLine.objects.filter(company_id=self.get_company_id())
        t = self.request.query_params.get("transfer_id")
        if t:
            qs = qs.filter(transfer_id=t)
        return qs

    def perform_create(self, serializer):
        serializer.instance = TransferLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_update(self, serializer):
        serializer.instance = TransferLineService.update(
            company_id=self.get_company_id(),
            line_id=serializer.instance.id,
            quantity=serializer.validated_data.get(
                "quantity", serializer.instance.quantity,
            ),
        )


# --- Списание ---

class WriteOffViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WriteOffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WriteOff.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("lines")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-writeoff_date")

    def perform_create(self, serializer):
        serializer.instance = WriteOffService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        wo = self.get_object()
        try:
            wo = WriteOffService.post(
                company_id=self.get_company_id(), writeoff_id=wo.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(WriteOffSerializer(wo).data)

    @action(detail=True, methods=["post"])
    def unpost(self, request, pk=None):
        wo = self.get_object()
        try:
            wo = WriteOffService.unpost(
                company_id=self.get_company_id(), writeoff_id=wo.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(WriteOffSerializer(wo).data)


class WriteOffLineViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = WriteOffLineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = WriteOffLine.objects.filter(company_id=self.get_company_id())
        w = self.request.query_params.get("writeoff_id")
        if w:
            qs = qs.filter(writeoff_id=w)
        return qs

    def perform_create(self, serializer):
        serializer.instance = WriteOffLineService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


# --- Инвентаризация ---

class InventorySnapshotViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = InventorySnapshotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = InventorySnapshot.objects.filter(
            company_id=self.get_company_id(),
        ).prefetch_related("items")
        if self.action == "list":
            st = self.request.query_params.get("status")
            if st:
                qs = qs.filter(status=st)
        return qs.order_by("-snapshot_date")

    def perform_create(self, serializer):
        serializer.instance = InventorySnapshotService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    @action(detail=True, methods=["post"], url_path="finish-counting")
    def finish_counting(self, request, pk=None):
        snap = self.get_object()
        try:
            snap = InventorySnapshotService.finish_counting(
                company_id=self.get_company_id(), snapshot_id=snap.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(InventorySnapshotSerializer(snap).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        snap = self.get_object()
        try:
            snap = InventorySnapshotService.approve(
                company_id=self.get_company_id(), snapshot_id=snap.id,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(InventorySnapshotSerializer(snap).data)


class InventorySnapshotItemViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = InventorySnapshotItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = InventorySnapshotItem.objects.filter(company_id=self.get_company_id())
        s = self.request.query_params.get("snapshot_id")
        if s:
            qs = qs.filter(snapshot_id=s)
        return qs

    @action(detail=True, methods=["post"], url_path="record-count")
    def record_count(self, request, pk=None):
        item = self.get_object()
        val = request.data.get("counted_quantity")
        if val is None:
            raise ValidationError("counted_quantity обязателен")
        try:
            item = InventorySnapshotItemService.record_count(
                company_id=self.get_company_id(),
                snapshot_item_id=item.id, counted_quantity=val,
            )
        except ValueError as e:
            raise ValidationError(str(e))
        return Response(InventorySnapshotItemSerializer(item).data)


# --- Тара ---

class ContainerTypeViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContainerTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContainerType.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = ContainerTypeService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class ContainerViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContainerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Container.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = ContainerService.create(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )


class ContainerItemViewSet(CompanyScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContainerItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ContainerItem.objects.filter(company_id=self.get_company_id())

    def perform_create(self, serializer):
        serializer.instance = ContainerItemService.add(
            company_id=self.get_company_id(),
            data=dict(serializer.validated_data),
        )

    def perform_destroy(self, instance):
        ContainerItemService.remove(
            company_id=self.get_company_id(), container_item_id=instance.id,
        )