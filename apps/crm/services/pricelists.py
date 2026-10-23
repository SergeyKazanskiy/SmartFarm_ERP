"""
Прайс-листы (OP-CRM-20…22).
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import CRMEvents as CRM

from apps.crm.models import PriceList, PriceListItem
from apps.crm.services.helpers import gen_code


class PriceListService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-CRM-20."""
        pl = PriceList.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("PL"),
            name=data["name"],
            valid_from=data.get("valid_from"),
        )
        EventBus.publish(
            CRM.PRICE_LIST_CREATE,
            company_id=company_id,
            payload={"price_list_id": pl.id, "name": pl.name},
        )
        return pl


class PriceListItemService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-CRM-21."""
        item = PriceListItem.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("PLI"),
            price_list_id=data["price_list_id"],
            item_type=data["item_type"],
            material_id=data.get("material_id"),
            service_name=data.get("service_name", ""),
            unit_id=data.get("unit_id"),
            price=data["price"],
        )
        EventBus.publish(
            CRM.PRICE_LIST_ITEM_CREATE,
            company_id=company_id,
            payload={"price_list_item_id": item.id},
        )
        return item

    @staticmethod
    @transaction.atomic
    def update_price(*, company_id: int, price_list_item_id: int, price):
        """OP-CRM-22."""
        item = PriceListItem.objects.select_for_update().get(
            pk=price_list_item_id, company_id=company_id,
        )
        item.price = price
        item.save(update_fields=["price", "updated_at"])

        EventBus.publish(
            CRM.PRICE_LIST_ITEM_UPDATE_PRICE,
            company_id=company_id,
            payload={
                "price_list_item_id": item.id,
                "price": float(item.price),
            },
        )
        return item