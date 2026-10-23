from rest_framework.routers import DefaultRouter

from apps.wms.api.views import (
    ContainerItemViewSet, ContainerTypeViewSet, ContainerViewSet,
    GoodsReceiptLineViewSet, GoodsReceiptViewSet,
    InventorySnapshotItemViewSet, InventorySnapshotViewSet,
    InventoryTransactionViewSet, InventoryViewSet,
    MaterialGroupViewSet, MaterialLotViewSet,
    MaterialReservationViewSet, MaterialViewSet,
    SerialNumberViewSet, StorageLocationViewSet,
    TransferLineViewSet, TransferViewSet,
    WarehouseTypeViewSet, WarehouseViewSet,
    WriteOffLineViewSet, WriteOffViewSet,
)

router = DefaultRouter()
router.register("wms/warehouse-types", WarehouseTypeViewSet, basename="wms-warehouse-types")
router.register("wms/warehouses", WarehouseViewSet, basename="wms-warehouses")
router.register("wms/storage-locations", StorageLocationViewSet, basename="wms-storage-locations")
router.register("wms/material-groups", MaterialGroupViewSet, basename="wms-material-groups")
router.register("wms/materials", MaterialViewSet, basename="wms-materials")
router.register("wms/material-lots", MaterialLotViewSet, basename="wms-material-lots")
router.register("wms/serial-numbers", SerialNumberViewSet, basename="wms-serial-numbers")
router.register("wms/inventory", InventoryViewSet, basename="wms-inventory")
router.register("wms/inventory-transactions", InventoryTransactionViewSet, basename="wms-inventory-transactions")
router.register("wms/goods-receipts", GoodsReceiptViewSet, basename="wms-goods-receipts")
router.register("wms/goods-receipt-lines", GoodsReceiptLineViewSet, basename="wms-goods-receipt-lines")
router.register("wms/reservations", MaterialReservationViewSet, basename="wms-reservations")
router.register("wms/transfers", TransferViewSet, basename="wms-transfers")
router.register("wms/transfer-lines", TransferLineViewSet, basename="wms-transfer-lines")
router.register("wms/writeoffs", WriteOffViewSet, basename="wms-writeoffs")
router.register("wms/writeoff-lines", WriteOffLineViewSet, basename="wms-writeoff-lines")
router.register("wms/inventory-snapshots", InventorySnapshotViewSet, basename="wms-inventory-snapshots")
router.register("wms/inventory-snapshot-items", InventorySnapshotItemViewSet, basename="wms-inventory-snapshot-items")
router.register("wms/container-types", ContainerTypeViewSet, basename="wms-container-types")
router.register("wms/containers", ContainerViewSet, basename="wms-containers")
router.register("wms/container-items", ContainerItemViewSet, basename="wms-container-items")

urlpatterns = router.urls