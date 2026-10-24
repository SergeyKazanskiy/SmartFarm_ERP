"""
Заявки на закупку (OP-PROC-03…06).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import ProcurementEvents as PE

from apps.procurement.models import Requisition, RequisitionLine
from apps.procurement.services.helpers import gen_code


class RequisitionService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict,
               actor_employee_id: int | None = None):
        """OP-PROC-03."""
        req = Requisition.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("REQ"),
            requisition_number=data["requisition_number"],
            source_type=data.get("source_type", "manual"),
            source_id=data.get("source_id"),
            requisition_date=data["requisition_date"],
            requested_by_employee_id=(
                data.get("requested_by_employee_id") or actor_employee_id
            ),
            status="draft",
            planned_order_date=data.get("planned_order_date"),
            required_date=data.get("required_date"),
        )
        EventBus.publish(
            PE.REQUISITION_CREATE,
            company_id=company_id,
            payload={
                "requisition_id": req.id,
                "requisition_number": req.requisition_number,
                "source_type": req.source_type,
                "source_id": req.source_id,
            },
        )
        return req

    @staticmethod
    @transaction.atomic
    def review(*, company_id: int, requisition_id: int, new_status: str):
        """OP-PROC-06: approve / reject."""
        if new_status not in ("approved", "rejected"):
            raise ValueError(_("Допустимые статусы: approved / rejected"))

        req = Requisition.objects.select_for_update().get(
            pk=requisition_id, company_id=company_id,
        )
        if req.status != "pending_approval":
            raise ValueError(
                _("Согласовать можно только заявку в статусе pending_approval")
            )
        old = req.status
        req.status = new_status
        req.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PE.REQUISITION_REVIEW,
            company_id=company_id,
            payload={
                "requisition_id": req.id,
                "old_status": old,
                "new_status": new_status,
                "source_type": req.source_type,
                "source_id": req.source_id,
            },
        )
        return req

    @staticmethod
    @transaction.atomic
    def submit(*, company_id: int, requisition_id: int):
        """Промежуточный шаг — отправить на согласование."""
        req = Requisition.objects.select_for_update().get(
            pk=requisition_id, company_id=company_id,
        )
        if req.status != "draft":
            raise ValueError(_("Отправить можно только черновик"))
        req.status = "pending_approval"
        req.save(update_fields=["status", "updated_at"])
        return req


class RequisitionLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROC-04."""
        line = RequisitionLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("REQL"),
            requisition_id=data["requisition_id"],
            material_id=data["material_id"],
            quantity=data["quantity"],
            unit_id=data.get("unit_id"),
            estimated_unit_cost=data.get("estimated_unit_cost"),
        )
        EventBus.publish(
            PE.REQUISITION_LINE_CREATE,
            company_id=company_id,
            payload={
                "requisition_line_id": line.id,
                "requisition_id": line.requisition_id,
            },
        )
        return line

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, line_id: int, data: dict):
        """OP-PROC-05."""
        line = RequisitionLine.objects.select_for_update().get(
            pk=line_id, company_id=company_id,
        )
        for field in ("quantity", "estimated_unit_cost"):
            if field in data:
                setattr(line, field, data[field])
        line.save()
        EventBus.publish(
            PE.REQUISITION_LINE_UPDATE,
            company_id=company_id,
            payload={"requisition_line_id": line.id},
        )
        return line