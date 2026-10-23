"""
Резервирование и выдача (OP-WMS-15…17).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import WMSEvents as WE

from apps.wms.models import Inventory, MaterialReservation
from apps.wms.services.helpers import gen_code
from apps.wms.services.inventory import InventoryTransactionService


class MaterialReservationService:

    @staticmethod
    @transaction.atomic
    def reserve(*, company_id: int, data: dict):
        """OP-WMS-15."""
        res = MaterialReservation.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("RES"),
            material_id=data["material_id"],
            warehouse_id=data.get("warehouse_id"),
            task_object_type=data.get("task_object_type", ""),
            task_object_id=data.get("task_object_id"),
            quantity=data["quantity"],
            status="reserved",
            reserved_at=timezone.now(),
        )
        EventBus.publish(
            WE.MATERIAL_RESERVE,
            company_id=company_id,
            payload={
                "reservation_id": res.id,
                "material_id": res.material_id,
                "quantity": float(res.quantity),
            },
        )
        return res

    @staticmethod
    @transaction.atomic
    def issue(*, company_id: int, reservation_id: int):
        """
        OP-WMS-16: выдача материала по резервированию.
        Списывает Inventory.quantity и создаёт InventoryTransaction(type='issue').
        """
        res = MaterialReservation.objects.select_for_update().get(
            pk=reservation_id, company_id=company_id,
        )
        if res.status != "reserved":
            raise ValueError(_("Выдать можно только зарезервированное"))

        # Ищем Inventory для этого материала на складе
        inv = Inventory.objects.select_for_update().filter(
            company_id=company_id,
            material_id=res.material_id,
            location__warehouse_id=res.warehouse_id,
        ).order_by("-quantity").first()

        if inv is None:
            raise ValueError(_("Остаток не найден на складе"))
        if inv.quantity < res.quantity:
            raise ValueError(_("Недостаточно остатка"))

        inv.quantity = inv.quantity - res.quantity
        inv.save(update_fields=["quantity", "updated_at"])

        InventoryTransactionService.record(
            company_id=company_id,
            inventory=inv,
            transaction_type="issue",
            quantity=-res.quantity,
            source_document_type="wms_material_reservation",
            source_document_id=res.id,
            reservation_id=res.id,
        )

        res.status = "issued"
        res.issued_at = timezone.now()
        res.save(update_fields=["status", "issued_at", "updated_at"])

        EventBus.publish(
            WE.MATERIAL_ISSUE,
            company_id=company_id,
            payload={
                "reservation_id": res.id,
                "material_id": res.material_id,
                "quantity": float(res.quantity),
            },
        )
        return res

    @staticmethod
    @transaction.atomic
    def release(*, company_id: int, reservation_id: int):
        """OP-WMS-17: снятие резерва без выдачи."""
        res = MaterialReservation.objects.select_for_update().get(
            pk=reservation_id, company_id=company_id,
        )
        if res.status != "reserved":
            raise ValueError(_("Снять можно только зарезервированное"))

        res.status = "released"
        res.released_at = timezone.now()
        res.save(update_fields=["status", "released_at", "updated_at"])

        EventBus.publish(
            WE.MATERIAL_RELEASE,
            company_id=company_id,
            payload={"reservation_id": res.id},
        )
        return res