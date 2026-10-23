"""
Инвентаризация (OP-WMS-27…30).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import WMSEvents as WE

from apps.wms.models import (
    Inventory, InventorySnapshot, InventorySnapshotItem,
)
from apps.wms.services.helpers import gen_code
from apps.wms.services.inventory import InventoryTransactionService


class InventorySnapshotService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """
        OP-WMS-27: создание снимка.
        Автоматически формирует позиции по всем остаткам склада.
        """
        snap = InventorySnapshot.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SNP"),
            warehouse_id=data["warehouse_id"],
            snapshot_date=timezone.now(),
            status="draft",
        )

        # Снимок текущих остатков
        inventories = Inventory.objects.filter(
            company_id=company_id,
            location__warehouse_id=snap.warehouse_id,
        )
        for inv in inventories:
            InventorySnapshotItem.objects.create(
                company_id=company_id,
                code=gen_code("SNI"),
                snapshot=snap,
                inventory=inv,
                quantity=inv.quantity,
            )

        EventBus.publish(
            WE.SNAPSHOT_CREATE,
            company_id=company_id,
            payload={"snapshot_id": snap.id, "warehouse_id": snap.warehouse_id},
        )
        return snap

    @staticmethod
    @transaction.atomic
    def finish_counting(*, company_id: int, snapshot_id: int):
        """OP-WMS-29."""
        snap = InventorySnapshot.objects.select_for_update().get(
            pk=snapshot_id, company_id=company_id,
        )
        if snap.status != "draft":
            raise ValueError(_("Завершить можно только draft"))
        snap.status = "counted"
        snap.save(update_fields=["status", "updated_at"])
        EventBus.publish(
            WE.SNAPSHOT_FINISH_COUNTING,
            company_id=company_id,
            payload={"snapshot_id": snap.id},
        )
        return snap

    @staticmethod
    @transaction.atomic
    def approve(*, company_id: int, snapshot_id: int):
        """
        OP-WMS-30: утверждение.
        Для каждой позиции:
        - если counted > quantity → InventoryTransaction('receipt', +delta);
        - если counted < quantity → InventoryTransaction('writeoff', -delta);
        - обновить Inventory.quantity до counted.
        """
        snap = InventorySnapshot.objects.select_for_update().get(
            pk=snapshot_id, company_id=company_id,
        )
        if snap.status != "counted":
            raise ValueError(_("Утвердить можно только пересчитанный снимок"))

        for item in snap.items.select_related("inventory").all():
            if item.counted_quantity is None:
                raise ValueError(
                    _("Не внесён пересчёт по позиции %(code)s")
                    % {"code": item.code}
                )
            delta = item.counted_quantity - item.quantity

            if delta == 0:
                continue

            inv = item.inventory
            inv.quantity = item.counted_quantity
            inv.save(update_fields=["quantity", "updated_at"])

            if delta > 0:
                InventoryTransactionService.record(
                    company_id=company_id,
                    inventory=inv,
                    transaction_type="receipt",
                    quantity=delta,
                    source_document_type="wms_inventory_snapshot",
                    source_document_id=snap.id,
                )
            else:
                InventoryTransactionService.record(
                    company_id=company_id,
                    inventory=inv,
                    transaction_type="writeoff",
                    quantity=delta,
                    source_document_type="wms_inventory_snapshot",
                    source_document_id=snap.id,
                )

        snap.status = "approved"
        snap.save(update_fields=["status", "updated_at"])
        EventBus.publish(
            WE.SNAPSHOT_APPROVE,
            company_id=company_id,
            payload={"snapshot_id": snap.id},
        )
        return snap


class InventorySnapshotItemService:

    @staticmethod
    @transaction.atomic
    def record_count(*, company_id: int, snapshot_item_id: int, counted_quantity):
        """OP-WMS-28."""
        item = InventorySnapshotItem.objects.select_for_update().get(
            pk=snapshot_item_id, company_id=company_id,
        )
        if item.snapshot.status not in ("draft", "counted"):
            raise ValueError(_("Нельзя вносить пересчёт в утверждённый снимок"))
        item.counted_quantity = counted_quantity
        item.save(update_fields=["counted_quantity", "updated_at"])
        EventBus.publish(
            WE.SNAPSHOT_ITEM_RECORD_COUNT,
            company_id=company_id,
            payload={"snapshot_item_id": item.id, "snapshot_id": item.snapshot_id},
        )
        return item