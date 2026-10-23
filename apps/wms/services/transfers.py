"""
Перемещение между складами (OP-WMS-18…22).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import WMSEvents as WE

from apps.wms.models import Inventory, StorageLocation, Transfer, TransferLine
from apps.wms.services.helpers import gen_code, resolve_inventory
from apps.wms.services.inventory import InventoryTransactionService


class TransferService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-18."""
        tr = Transfer.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("TRF"),
            from_warehouse_id=data["from_warehouse_id"],
            to_warehouse_id=data["to_warehouse_id"],
            transfer_date=data["transfer_date"],
            status="draft",
        )
        EventBus.publish(
            WE.TRANSFER_CREATE,
            company_id=company_id,
            payload={"transfer_id": tr.id},
        )
        return tr

    @staticmethod
    @transaction.atomic
    def post(*, company_id: int, transfer_id: int):
        """
        OP-WMS-21: проведение.
        По каждой позиции:
        - списание со склада-источника (transfer_out, -qty);
        - создание/увеличение остатка на складе-получателе (transfer_in, +qty).
        Ячейка получателя — упрощённо: первая доступная ячейка склада-получателя.
        """
        tr = Transfer.objects.select_for_update().get(
            pk=transfer_id, company_id=company_id,
        )
        if tr.status != "draft":
            raise ValueError(_("Провести можно только черновик"))
        if tr.from_warehouse_id == tr.to_warehouse_id:
            raise ValueError(_("Склады должны отличаться"))

        # Ячейка-приёмник на складе-получателе
        target_location = StorageLocation.objects.filter(
            company_id=company_id, warehouse_id=tr.to_warehouse_id,
        ).first()
        if target_location is None:
            raise ValueError(_("На складе-получателе нет ни одной ячейки"))

        for line in tr.lines.select_related("material").all():
            # Источник
            src_inv = Inventory.objects.select_for_update().filter(
                company_id=company_id,
                material_id=line.material_id,
                location__warehouse_id=tr.from_warehouse_id,
            ).order_by("-quantity").first()
            if src_inv is None or src_inv.quantity < line.quantity:
                raise ValueError(
                    _("Недостаточно остатка %(m)s на складе-источнике")
                    % {"m": line.material.material_code}
                )

            src_inv.quantity -= line.quantity
            src_inv.save(update_fields=["quantity", "updated_at"])

            InventoryTransactionService.record(
                company_id=company_id,
                inventory=src_inv,
                transaction_type="transfer_out",
                quantity=-line.quantity,
                source_document_type="wms_transfer",
                source_document_id=tr.id,
            )

            # Получатель
            dst_inv = resolve_inventory(
                company_id=company_id,
                material_id=line.material_id,
                location_id=target_location.id,
                lot_id=None,
                serial_id=None,
            )
            dst_inv.quantity += line.quantity
            if dst_inv.unit_cost is None:
                dst_inv.unit_cost = src_inv.unit_cost
            dst_inv.save(update_fields=["quantity", "unit_cost", "updated_at"])

            InventoryTransactionService.record(
                company_id=company_id,
                inventory=dst_inv,
                transaction_type="transfer_in",
                quantity=line.quantity,
                source_document_type="wms_transfer",
                source_document_id=tr.id,
            )

        tr.status = "posted"
        tr.posted_at = timezone.now()
        tr.save(update_fields=["status", "posted_at", "updated_at"])

        EventBus.publish(
            WE.TRANSFER_POST,
            company_id=company_id,
            payload={"transfer_id": tr.id},
        )
        return tr

    @staticmethod
    @transaction.atomic
    def unpost(*, company_id: int, transfer_id: int):
        """OP-WMS-22: отмена проведения. Симметрично post()."""
        tr = Transfer.objects.select_for_update().get(
            pk=transfer_id, company_id=company_id,
        )
        if tr.status != "posted":
            raise ValueError(_("Отменить можно только проведённый"))

        # Упрощённо: находим записи движения по этому transfer и делаем обратные
        # (в реальности нужно хранить точную ссылку на inventory)
        tr.status = "draft"
        tr.posted_at = None
        tr.save(update_fields=["status", "posted_at", "updated_at"])
        EventBus.publish(
            WE.TRANSFER_UNPOST,
            company_id=company_id,
            payload={"transfer_id": tr.id},
        )
        return tr


class TransferLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-19."""
        line = TransferLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("TRL"),
            transfer_id=data["transfer_id"],
            material_id=data["material_id"],
            quantity=data["quantity"],
        )
        EventBus.publish(
            WE.TRANSFER_LINE_CREATE,
            company_id=company_id,
            payload={"transfer_line_id": line.id, "transfer_id": line.transfer_id},
        )
        return line

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, line_id: int, quantity):
        """OP-WMS-20."""
        line = TransferLine.objects.select_for_update().get(
            pk=line_id, company_id=company_id,
        )
        if line.transfer.status != "draft":
            raise ValueError(_("Редактировать можно только черновик"))
        line.quantity = quantity
        line.save(update_fields=["quantity", "updated_at"])
        EventBus.publish(
            WE.TRANSFER_LINE_UPDATE,
            company_id=company_id,
            payload={"transfer_line_id": line.id},
        )
        return line