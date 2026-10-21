"""
Чёрный список (OP-CP-26, OP-CP-27).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus
from core.events import CPEvents as CP

from apps.cp.models import Blacklist, Counterparty


class BlacklistService:

    @staticmethod
    @transaction.atomic
    def add(*, company_id: int, counterparty_id: int, reason: str,
            actor_employee_id: int | None = None):
        """OP-CP-26: блокировка контрагента."""
        cp = Counterparty.objects.select_for_update().get(
            pk=counterparty_id, company_id=company_id,
        )

        entry = Blacklist.objects.create(
            company_id=company_id,
            counterparty_id=counterparty_id,
            block_date=timezone.now().date(),
            reason=reason,
            blocked_by_employee_id=actor_employee_id,
        )

        cp.is_blacklisted = True
        cp.status = "blacklisted"
        cp.save(update_fields=["is_blacklisted", "status", "updated_at"])

        EventBus.publish(
            CP.BLACKLIST_ADD,
            company_id=company_id,
            payload={
                "blacklist_id": entry.id,
                "counterparty_id": counterparty_id,
                "reason": reason,
            },
        )
        return entry

    @staticmethod
    @transaction.atomic
    def remove(*, company_id: int, counterparty_id: int,
               unblock_reason: str, actor_employee_id: int | None = None):
        """OP-CP-27: разблокировка."""
        cp = Counterparty.objects.select_for_update().get(
            pk=counterparty_id, company_id=company_id,
        )
        active_block = Blacklist.objects.filter(
            counterparty_id=counterparty_id, unblock_date__isnull=True,
        ).first()
        if active_block is None:
            raise ValueError("Активной блокировки не найдено")

        active_block.unblock_date = timezone.now().date()
        active_block.unblock_reason = unblock_reason
        active_block.unblocked_by_employee_id = actor_employee_id
        active_block.save(update_fields=[
            "unblock_date", "unblock_reason", "unblocked_by_employee_id",
        ])

        cp.is_blacklisted = False
        cp.status = "active"
        cp.save(update_fields=["is_blacklisted", "status", "updated_at"])

        EventBus.publish(
            CP.BLACKLIST_REMOVE,
            company_id=company_id,
            payload={
                "counterparty_id": counterparty_id,
                "unblock_reason": unblock_reason,
            },
        )
        return cp