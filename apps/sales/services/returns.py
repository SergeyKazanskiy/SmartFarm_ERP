"""
Возвраты (OP-SALES-25…28).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import Return, ReturnLine
from apps.sales.services.helpers import gen_code


class ReturnService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-SALES-25."""
        ret = Return.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("RET"),
            return_number=data["return_number"],
            order_id=data["order_id"],
            return_date=data["return_date"],
            reason=data.get("reason", ""),
            status="draft",
        )

        EventBus.publish(
            SE.RETURN_SAVE,
            company_id=company_id,
            payload={
                "return_id": ret.id,
                "order_id": ret.order_id,
            },
        )
        return ret

    @staticmethod
    @transaction.atomic
    def approve(*, company_id: int, return_id: int):
        """OP-SALES-27. draft → approved."""
        ret = Return.objects.select_for_update().get(
            pk=return_id, company_id=company_id,
        )
        if ret.status != "draft":
            raise ValueError(_("Утвердить можно только черновик"))
        ret.status = "approved"
        ret.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.RETURN_APPROVE,
            company_id=company_id,
            payload={"return_id": ret.id, "order_id": ret.order_id},
        )
        return ret

    @staticmethod
    @transaction.atomic
    def receive(*, company_id: int, return_id: int):
        """OP-SALES-28. approved → received."""
        ret = Return.objects.select_for_update().get(
            pk=return_id, company_id=company_id,
        )
        if ret.status != "approved":
            raise ValueError(_("Принять можно только утверждённый возврат"))
        ret.status = "received"
        ret.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.RETURN_RECEIVE,
            company_id=company_id,
            payload={"return_id": ret.id, "order_id": ret.order_id},
        )
        return ret


class ReturnLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-SALES-26."""
        line = ReturnLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("RTL"),
            return_id=data["return_id"],
            order_line_id=data["order_line_id"],
            quantity=data["quantity"],
        )
        return line