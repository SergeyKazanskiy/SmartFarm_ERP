"""
Коммерческие предложения (OP-CRM-15…19).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import CRMEvents as CRM

from apps.crm.models import CommercialOffer, CommercialOfferLine
from apps.crm.services.helpers import gen_code


class CommercialOfferService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-CRM-15: создание КП в статусе draft."""
        offer = CommercialOffer.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("OFFER"),
            opportunity_id=data["opportunity_id"],
            offer_date=data.get("offer_date"),
            status="draft",
        )

        EventBus.publish(
            CRM.COMMERCIAL_OFFER_CREATE,
            company_id=company_id,
            payload={
                "offer_id": offer.id,
                "opportunity_id": offer.opportunity_id,
            },
        )
        return offer

    @staticmethod
    @transaction.atomic
    def send(*, company_id: int, offer_id: int):
        """OP-CRM-17: отправка (draft → sent). Пересчёт total_amount."""
        offer = CommercialOffer.objects.select_for_update().get(
            pk=offer_id, company_id=company_id,
        )
        if offer.status != "draft":
            raise ValueError(_("Отправить можно только черновик"))

        total = (
            offer.lines.aggregate(s=Sum("line_amount"))["s"] or Decimal("0")
        )
        offer.status = "sent"
        offer.total_amount = total
        offer.save(update_fields=["status", "total_amount", "updated_at"])

        EventBus.publish(
            CRM.COMMERCIAL_OFFER_SEND,
            company_id=company_id,
            payload={
                "offer_id": offer.id,
                "opportunity_id": offer.opportunity_id,
                "total_amount": float(total),
            },
        )
        return offer

    @staticmethod
    @transaction.atomic
    def accept(*, company_id: int, offer_id: int):
        """OP-CRM-18: клиент принял (sent → accepted)."""
        offer = CommercialOffer.objects.select_for_update().get(
            pk=offer_id, company_id=company_id,
        )
        if offer.status != "sent":
            raise ValueError(_("Принять можно только отправленное КП"))

        offer.status = "accepted"
        offer.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            CRM.COMMERCIAL_OFFER_ACCEPT,
            company_id=company_id,
            payload={
                "offer_id": offer.id,
                "opportunity_id": offer.opportunity_id,
            },
        )
        return offer

    @staticmethod
    @transaction.atomic
    def decline(*, company_id: int, offer_id: int):
        """OP-CRM-19."""
        offer = CommercialOffer.objects.select_for_update().get(
            pk=offer_id, company_id=company_id,
        )
        if offer.status != "sent":
            raise ValueError(_("Отклонить можно только отправленное КП"))

        offer.status = "declined"
        offer.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            CRM.COMMERCIAL_OFFER_DECLINE,
            company_id=company_id,
            payload={
                "offer_id": offer.id,
                "opportunity_id": offer.opportunity_id,
            },
        )
        return offer


class CommercialOfferLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-CRM-16: добавление позиции. line_amount считается автоматически."""
        qty = Decimal(str(data["quantity"]))
        price = Decimal(str(data["unit_price"]))
        line_amount = (qty * price).quantize(Decimal("0.01"))

        line = CommercialOfferLine.objects.create(
            company_id=company_id,
            offer_id=data["offer_id"],
            price_list_item_id=data.get("price_list_item_id"),
            description=data["description"],
            quantity=qty,
            unit_price=price,
            line_amount=line_amount,
        )

        EventBus.publish(
            CRM.COMMERCIAL_OFFER_LINE_CREATE,
            company_id=company_id,
            payload={
                "offer_line_id": line.id,
                "offer_id": line.offer_id,
            },
        )
        return line