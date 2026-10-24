"""
Запросы предложений (OP-PROC-07…11).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import ProcurementEvents as PE

from apps.procurement.models import RFQ, RFQSupplier, SupplierQuote
from apps.procurement.services.helpers import gen_code


class RFQService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROC-07."""
        rfq = RFQ.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("RFQ"),
            rfq_number=data["rfq_number"],
            requisition_id=data.get("requisition_id"),
            rfq_date=data["rfq_date"],
            response_deadline=data.get("response_deadline"),
            status="draft",
        )
        EventBus.publish(
            PE.RFQ_CREATE,
            company_id=company_id,
            payload={
                "rfq_id": rfq.id,
                "requisition_id": rfq.requisition_id,
            },
        )
        return rfq

    @staticmethod
    @transaction.atomic
    def send(*, company_id: int, rfq_id: int):
        """OP-PROC-09: draft → sent."""
        rfq = RFQ.objects.select_for_update().get(
            pk=rfq_id, company_id=company_id,
        )
        if rfq.status != "draft":
            raise ValueError(_("Отправить можно только черновик"))
        rfq.status = "sent"
        rfq.save(update_fields=["status", "updated_at"])
        return rfq

    @staticmethod
    @transaction.atomic
    def mark_responded(*, company_id: int, rfq_id: int):
        """Промежуточное: поставщики прислали предложения."""
        rfq = RFQ.objects.select_for_update().get(
            pk=rfq_id, company_id=company_id,
        )
        if rfq.status != "sent":
            raise ValueError(_("Ответы возможны только для отправленного RFQ"))
        rfq.status = "responded"
        rfq.save(update_fields=["status", "updated_at"])
        return rfq

    @staticmethod
    @transaction.atomic
    def close(*, company_id: int, rfq_id: int):
        """OP-PROC-11: responded → closed."""
        rfq = RFQ.objects.select_for_update().get(
            pk=rfq_id, company_id=company_id,
        )
        if rfq.status != "responded":
            raise ValueError(_("Закрыть можно только responded RFQ"))
        rfq.status = "closed"
        rfq.save(update_fields=["status", "updated_at"])
        EventBus.publish(
            PE.RFQ_CLOSE,
            company_id=company_id,
            payload={
                "rfq_id": rfq.id,
                "requisition_id": rfq.requisition_id,
            },
        )
        return rfq


class RFQSupplierService:

    @staticmethod
    @transaction.atomic
    def add(*, company_id: int, data: dict):
        """OP-PROC-08."""
        link = RFQSupplier.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("RFS"),
            rfq_id=data["rfq_id"],
            supplier_id=data["supplier_id"],
        )
        EventBus.publish(
            PE.RFQ_SUPPLIER_ADD,
            company_id=company_id,
            payload={
                "rfq_supplier_id": link.id,
                "rfq_id": link.rfq_id,
                "supplier_id": link.supplier_id,
            },
        )
        return link


class SupplierQuoteService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROC-10."""
        quote = SupplierQuote.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("SQ"),
            rfq_supplier_id=data["rfq_supplier_id"],
            material_id=data["material_id"],
            unit_price=data["unit_price"],
            quantity=data["quantity"],
            delivery_days=data.get("delivery_days"),
        )
        EventBus.publish(
            PE.SUPPLIER_QUOTE_CREATE,
            company_id=company_id,
            payload={
                "quote_id": quote.id,
                "rfq_supplier_id": quote.rfq_supplier_id,
                "material_id": quote.material_id,
            },
        )
        return quote