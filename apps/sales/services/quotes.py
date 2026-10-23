"""
Коммерческие предложения (OP-SALES-09…12).
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import Quote, QuoteLine
from apps.sales.services.helpers import calc_line_total, gen_code


class QuoteService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict,
               actor_employee_id: int | None = None):
        """OP-SALES-09."""
        quote = Quote.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("QUOTE"),
            quote_number=data["quote_number"],
            customer_id=data["customer_id"],
            opportunity_id=data.get("opportunity_id"),
            quote_date=data["quote_date"],
            valid_until=data.get("valid_until"),
            status="draft",
            total_amount=Decimal("0"),
            created_by_employee_id=actor_employee_id,
        )

        EventBus.publish(
            SE.QUOTE_CREATE,
            company_id=company_id,
            payload={
                "quote_id": quote.id,
                "customer_id": quote.customer_id,
            },
        )
        return quote

    @staticmethod
    @transaction.atomic
    def send(*, company_id: int, quote_id: int):
        """OP-SALES-11. draft → sent."""
        q = Quote.objects.select_for_update().get(
            pk=quote_id, company_id=company_id,
        )
        if q.status != "draft":
            raise ValueError(_("Отправить можно только черновик"))
        q.status = "sent"
        q.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.QUOTE_CREATE,
            company_id=company_id,
            payload={"quote_id": q.id, "action": "send"},
        )
        return q

    @staticmethod
    @transaction.atomic
    def accept(*, company_id: int, quote_id: int):
        """OP-SALES-12. sent → accepted."""
        q = Quote.objects.select_for_update().get(
            pk=quote_id, company_id=company_id,
        )
        if q.status != "sent":
            raise ValueError(_("Принять можно только отправленное КП"))
        q.status = "accepted"
        q.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            SE.QUOTE_ACCEPT,
            company_id=company_id,
            payload={
                "quote_id": q.id,
                "customer_id": q.customer_id,
                "opportunity_id": q.opportunity_id,
            },
        )
        return q

    @staticmethod
    def _recalc_total(quote: Quote) -> None:
        """Пересчёт total_amount по всем позициям."""
        total = (
            quote.lines.aggregate(s=Sum("total_price"))["s"] or Decimal("0")
        )
        quote.total_amount = total
        quote.save(update_fields=["total_amount", "updated_at"])


class QuoteLineService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-SALES-10. Авторасчёт total_price + пересчёт quote.total_amount."""
        line = QuoteLine.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("QL"),
            quote_id=data["quote_id"],
            material_id=data["material_id"],
            price_list_item_id=data.get("price_list_item_id"),
            quantity=data["quantity"],
            unit_price=data["unit_price"],
            discount_percent=data.get("discount_percent", 0),
        )
        line.total_price = calc_line_total(
            line.quantity, line.unit_price, line.discount_percent,
        )
        line.save(update_fields=["total_price"])

        # Пересчитываем sum у quote
        QuoteService._recalc_total(line.quote)

        EventBus.publish(
            SE.QUOTE_LINE_CREATE,
            company_id=company_id,
            payload={
                "quote_line_id": line.id,
                "quote_id": line.quote_id,
                "total_price": float(line.total_price),
            },
        )
        return line

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, line_id: int):
        line = QuoteLine.objects.get(pk=line_id, company_id=company_id)
        quote = line.quote
        line.delete()
        QuoteService._recalc_total(quote)