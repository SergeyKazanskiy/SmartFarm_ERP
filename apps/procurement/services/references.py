"""
Поставщики (OP-PROC-01…02).
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import ProcurementEvents as PE

from apps.procurement.models import Supplier
from apps.procurement.services.helpers import gen_code


class SupplierService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: Supplier | None = None):
        """OP-PROC-01 / OP-PROC-02."""
        if instance is None:
            instance = Supplier(
                company_id=company_id,
                code=data.get("code") or gen_code("SUP"),
            )
        for field in (
            "counterparty_id", "rating", "payment_terms", "delivery_terms",
            "lead_time_days", "is_preferred",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PE.SUPPLIER_SAVE,
            company_id=company_id,
            payload={
                "supplier_id": instance.id,
                "code": instance.code,
                "counterparty_id": instance.counterparty_id,
            },
        )
        return instance