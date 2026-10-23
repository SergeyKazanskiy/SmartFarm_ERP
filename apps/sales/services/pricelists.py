"""Прайс-листы (OP-SALES-03…06)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import PriceList, PriceListLine
from apps.sales.services.helpers import gen_code


class PriceListService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: PriceList | None = None):
        if instance is None:
            instance = PriceList(
                company_id=company_id,
                code=data.get("code") or gen_code("PL"),
            )
        for field in (
            "name", "currency_id", "valid_from", "valid_to", "is_default",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        # Если is_default=True — снимаем флаг с других прайсов этой компании
        if instance.is_default:
            PriceList.objects.filter(
                company_id=company_id, is_default=True,
            ).exclude(pk=instance.pk).update(is_default=False)

        EventBus.publish(
            SE.PRICE_LIST_SAVE,
            company_id=company_id,
            payload={"price_list_id": instance.id, "code": instance.code},
        )
        return instance

    @staticmethod
    @transaction.atomic
    def deactivate(*, company_id: int, price_list_id: int):
        """OP-SALES-06."""
        pl = PriceList.objects.select_for_update().get(
            pk=price_list_id, company_id=company_id,
        )
        pl.valid_to = timezone.now().date()
        pl.save(update_fields=["valid_to", "updated_at"])
        return pl


class PriceListLineService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: PriceListLine | None = None):
        """OP-SALES-04 / OP-SALES-05."""
        if instance is None:
            instance = PriceListLine(
                company_id=company_id,
                code=data.get("code") or gen_code("PLL"),
            )
        for field in ("price_list_id", "material_id", "unit_price", "min_quantity"):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            SE.PRICE_LIST_ITEM_SAVE,
            company_id=company_id,
            payload={
                "price_list_line_id": instance.id,
                "price_list_id": instance.price_list_id,
            },
        )
        return instance