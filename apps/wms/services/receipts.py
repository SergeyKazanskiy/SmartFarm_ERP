"""
Приход материалов (OP-WMS-10…14).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import WMSEvents as WE

from apps.wms.models import GoodsReceipt, GoodsReceiptLine, Inventory
from apps.wms.services.helpers import (
    calc_moving_average, gen_code, resolve_inventory,
)
from apps.wms.services.inventory import InventoryTransactionService


class GoodsReceiptService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-10."""
        gr = GoodsReceipt.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("GR"),
            warehouse_id=data["warehouse_id"],
            counterparty_id=data.get("counterparty_id"),
            receipt_date=data["receipt_date"],
            document_id=data.get("document_id"),
            status="draft",
        )
        EventBus.publish(
            WE.GOODS_RECEIPT_CREATE,
            company_id=company_id,
            payload={"receipt_id": gr.id, "warehouse_id": gr.warehouse_id},
        )
        return gr

    @staticmethod
    @transaction.atomic
    def post(*, company_id: int, receipt_id: int):
        """
        OP-WMS-13: проведение приходного документа.
        По каждой позиции:
        - найти/создать Inventory по (material, location, lot, serial);
        - пересчитать unit_cost скользящим средним;
        - создать InventoryTransaction(type='receipt', source='wms_goods_receipt').
        """
        gr = GoodsReceipt.objects.select_for_update().get(
            pk=receipt_id, company_id=company_id,
        )
        if gr.status != "draft":
            raise ValueError(_("Провести можно только документ в статусе draft"))

        lines = gr.lines.select_related("material", "location", "lot").all()
        if not lines:
            raise ValueError(_("Нельзя провести пустой приход"))

        for line in lines:
            if line.location_id is None:
                raise ValueError(
                    _("В позиции %(code)s не указана ячейка размещения")
                    % {"code": line.code}
                )

            inv = resolve_inventory(
                company_id=company_id,
                material_id=line.material_id,
                location_id=line.location_id,
                lot_id=line.lot_id,
                serial_id=None,
            )

            old_qty = inv.quantity or Decimal("0")
            old_cost = inv.unit_cost
            new_qty = line.quantity
            new_cost = line.unit_cost

            # Пересчёт скользящего среднего
            inv.unit_cost = calc_moving_average(
                old_qty=old_qty,
                old_cost=old_cost,
                new_qty=new_qty,
                new_cost=new_cost,
            )
            inv.quantity = old_qty + new_qty
            inv.save(update_fields=["quantity", "unit_cost", "updated_at"])

            # Журнал
            InventoryTransactionService.record(
                company_id=company_id,
                inventory=inv,
                transaction_type="receipt",
                quantity=line.quantity,
                source_document_type="wms_goods_receipt",
                source_document_id=gr.id,
            )

        gr.status = "posted"
        gr.posted_at = timezone.now()
        gr.save(update_fields=["status", "posted_at", "updated_at"])

        EventBus.publish(
            WE.GOODS_RECEIPT_POST,
            company_id=company_id,
            payload={"receipt_id": gr.id, "warehouse_id": gr.warehouse_id},
        )
        return gr

    @staticmethod
    @transaction.atomic
    def unpost(*, company_id: int, receipt_id: int):
        """
        OP-WMS-14: отмена проведения.
        Возвращает остатки в исходное состояние.
        """
        gr = GoodsReceipt.objects.select_for_update().get(
            pk=receipt_id, company_id=company_id,
        )
        if gr.status != "posted":
            raise ValueError(_("Отменить можно только проведённый документ"))

        for line in gr.lines.select_related("material", "location", "lot").all():
            inv = Inventory.objects.select_for_update().filter(
                company_id=company_id,
                material_id=line.material_id,
                location_id=line.location_id,
                lot_id=line.lot_id,
            ).first()
            if inv is None:
                continue
            inv.quantity = (inv.quantity or Decimal("0")) - line.quantity
            inv.save(update_fields=["quantity", "updated_at"])

            InventoryTransactionService.record(
                company_id=company_id,
                inventory=inv,
                transaction_type="receipt",  # отрицательный receipt
                quantity=-line.quantity,
                source_document_type="wms_goods_receipt",
                source_document_id=gr.id,
            )

        gr.status = "draft"
        gr.posted_at = None
        gr.save(update_fields=["status", "posted_at", "updated_at"])

        EventBus.publish(
            WE.GOODS_RECEIPT_UNPOST,
            company_id=company_id,
            payload={"receipt_id": gr.id},
        )
        return gr


class GoodsReceiptLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-11."""
        line = GoodsReceiptLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("GRL"),
            receipt_id=data["receipt_id"],
            material_id=data["material_id"],
            lot_id=data.get("lot_id"),
            location_id=data.get("location_id"),
            quantity=data["quantity"],
            unit_cost=data.get("unit_cost"),
        )
        EventBus.publish(
            WE.GOODS_RECEIPT_LINE_CREATE,
            company_id=company_id,
            payload={"receipt_line_id": line.id, "receipt_id": line.receipt_id},
        )
        return line

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, line_id: int, data: dict):
        """OP-WMS-12."""
        line = GoodsReceiptLine.objects.select_for_update().get(
            pk=line_id, company_id=company_id,
        )
        if line.receipt.status != "draft":
            raise ValueError(_("Редактировать можно только черновик"))
        for field in ("quantity", "unit_cost", "location_id"):
            if field in data:
                setattr(line, field, data[field])
        line.save()
        EventBus.publish(
            WE.GOODS_RECEIPT_LINE_UPDATE,
            company_id=company_id,
            payload={"receipt_line_id": line.id},
        )
        return line