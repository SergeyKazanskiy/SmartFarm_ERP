"""
Справочники: типы контрагентов (OP-CP-01…02) и категории (OP-CP-03…04).
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import CPEvents as CP   # ← см. правку core/events.py ниже

from apps.cp.models import Category, CounterpartyType
from apps.cp.services.helpers import gen_code


class CounterpartyTypeService:
    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: CounterpartyType | None = None):
        """
        OP-CP-01 (создание) / OP-CP-02 (обновление).
        """
        if instance is None:
            instance = CounterpartyType(
                company_id=company_id,
                code=data.get("code") or gen_code("CPT"),
            )
        for field in ("name", "is_active"):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            CP.COUNTERPARTY_TYPE_SAVE,
            company_id=company_id,
            payload={"id": instance.id, "code": instance.code, "action": "save"},
        )
        return instance


class CategoryService:
    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Category | None = None):
        """OP-CP-03 / OP-CP-04."""
        if instance is None:
            instance = Category(
                company_id=company_id,
                code=data.get("code") or gen_code("CAT"),
            )
        for field in ("name", "parent_id", "is_active"):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            CP.CATEGORY_SAVE,
            company_id=company_id,
            payload={"id": instance.id, "code": instance.code, "action": "save"},
        )
        return instance