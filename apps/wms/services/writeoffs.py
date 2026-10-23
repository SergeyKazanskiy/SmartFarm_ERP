"""
Списание материалов (OP-WMS-23…26).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import WMSEvents as WE

from apps.wms.models import Inventory, WriteOff, WriteOffLine
from apps.wms.services.helpers import gen_code
from apps.wms.services.inventory import InventoryTransactionService


class WriteOffService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-23."""
        wo = WriteOff.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("WO"),
            warehouse_id=data["warehouse_id"],
            writeoff_date=data["writeoff_date"],
            reason=data.get("reason", ""),
            status="draft",
        )
        EventBus.publish(
            WE.WRITEOFF_CREATE,
            company_id=company_id,
            payload={"writeoff_id": wo.id, "warehouse_id": wo.warehouse_id},
        )
        return wo

    @staticmethod
    @transaction.atomic
    def post(*, company_id: int, writeoff_id: int):
        """OP-WMS-25: проведение списания."""
        wo = WriteOff.objects.select_for_update().get(
            pk=writeoff_id, company_id=company_id,
        )
        if wo.status != "draft":
            raise ValueError(_("Провести можно только черновик"))

        for line in wo.lines.select_related("material").all():
            inv = Inventory.objects.select_for_update().filter(
                company_id=company_id,
                material_id=line.material_id,
                location__warehouse_id=wo.warehouse_id,
            ).order_by("-quantity").first()

            if inv is None or inv.quantity < line.quantity:
                raise ValueError(
                    _("Недостаточно остатка %(m)s для списания")
                    % {"m": line.material.material_code}
                )

            inv.quantity -= line.quantity
            inv.save(update_fields=["quantity", "updated_at"])

            InventoryTransactionService.record(
                company_id=company_id,
                inventory=inv,
                transaction_type="writeoff",
                quantity=-line.quantity,
                source_document_type="wms_writeoff",
                source_document_id=wo.id,
            )

        wo.status = "posted"
        wo.posted_at = timezone.now()
        wo.save(update_fields=["status", "posted_at", "updated_at"])
        EventBus.publish(
            WE.WRITEOFF_POST,
            company_id=company_id,
            payload={"writeoff_id": wo.id},
        )
        return wo

    @staticmethod
    @transaction.atomic
    def unpost(*, company_id: int, writeoff_id: int):
        """OP-WMS-26."""
        wo = WriteOff.objects.select_for_update().get(
            pk=writeoff_id, company_id=company_id,
        )
        if wo.status != "posted":
            raise ValueError(_("Отменить можно только проведённое"))
        wo.status = "draft"
        wo.posted_at = None
        wo.save(update_fields=["status", "posted_at", "updated_at"])
        EventBus.publish(
            WE.WRITEOFF_UNPOST,
            company_id=company_id,
            payload={"writeoff_id": wo.id},
        )
        return wo


class WriteOffLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-WMS-24."""
        line = WriteOffLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("WOL"),
            writeoff_id=data["writeoff_id"],
            material_id=data["material_id"],
            quantity=data["quantity"],
        )
        EventBus.publish(
            WE.WRITEOFF_LINE_CREATE,
            company_id=company_id,
            payload={"writeoff_line_id": line.id, "writeoff_id": line.writeoff_id},
        )
        return line