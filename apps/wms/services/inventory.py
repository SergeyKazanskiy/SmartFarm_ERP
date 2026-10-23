"""
Остатки и журнал движений.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.event_bus import EventBus

from apps.wms.models import Inventory, InventoryTransaction
from apps.wms.services.helpers import gen_code


class InventoryService:

    @staticmethod
    def adjust_quantity(
        inventory: Inventory, delta: Decimal,
    ) -> Inventory:
        """Изменяет quantity остатка на delta (может быть отрицательной)."""
        inventory.quantity = (inventory.quantity or Decimal("0")) + delta
        inventory.save(update_fields=["quantity", "updated_at"])
        return inventory


class InventoryTransactionService:

    @staticmethod
    @transaction.atomic
    def record(
        *,
        company_id: int,
        inventory: Inventory,
        transaction_type: str,
        quantity: Decimal,
        source_document_type: str = "",
        source_document_id: int | None = None,
        reservation_id: int | None = None,
        task_id: int | None = None,
    ) -> InventoryTransaction:
        """
        Создаёт запись в журнале движений.
        `quantity` — со знаком: + для receipt/transfer_in, − для issue/writeoff/transfer_out.
        """
        return InventoryTransaction.objects.create(
            company_id=company_id,
            code=gen_code("IT"),
            inventory=inventory,
            transaction_type=transaction_type,
            quantity=quantity,
            source_document_type=source_document_type,
            source_document_id=source_document_id,
            reservation_id=reservation_id,
            task_id=task_id,
            transaction_date=timezone.now(),
        )