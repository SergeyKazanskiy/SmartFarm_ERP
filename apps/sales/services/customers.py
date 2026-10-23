"""Клиенты (OP-SALES-01…02)."""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus
from core.events import SalesEvents as SE

from apps.sales.models import Customer
from apps.sales.services.helpers import gen_code


class CustomerService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: Customer | None = None):
        if instance is None:
            instance = Customer(
                company_id=company_id,
                code=data.get("code") or gen_code("CUST"),
            )
        for field in (
            "counterparty_id", "category", "credit_limit",
            "payment_terms", "default_price_list_id",
            "sales_manager_employee_id", "is_active",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            SE.CUSTOMER_SAVE,
            company_id=company_id,
            payload={
                "customer_id": instance.id,
                "code": instance.code,
                "counterparty_id": instance.counterparty_id,
            },
        )
        return instance