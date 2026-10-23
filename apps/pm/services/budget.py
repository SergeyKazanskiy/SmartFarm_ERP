"""
Бюджет (OP-PM-24…25) и статьи (OP-PM-26…28).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import PMEvents as PM

from apps.pm.models import Budget, BudgetItem
from apps.pm.services.helpers import gen_code


class BudgetService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: Budget | None = None,
             actor_employee_id: int | None = None):
        """OP-PM-24 / OP-PM-25 (утверждение — отдельный метод)."""
        if instance is None:
            instance = Budget(
                company_id=company_id,
                code=data.get("code") or gen_code("BUD"),
                status="draft",
            )
        for field in (
            "project_id", "name",
            "total_planned_amount", "total_actual_amount", "currency_id",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.BUDGET_SAVE,
            company_id=company_id,
            payload={
                "budget_id": instance.id,
                "project_id": instance.project_id,
                "status": instance.status,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def approve(*, company_id: int, budget_id: int, approver_employee_id: int):
        """OP-PM-25."""
        budget = Budget.objects.select_for_update().get(
            pk=budget_id, company_id=company_id,
        )
        if budget.status != "draft":
            raise ValueError(_("Утвердить можно только черновик бюджета"))

        budget.status = "approved"
        budget.approved_by_employee_id = approver_employee_id
        budget.approved_at = timezone.now()
        budget.save(update_fields=[
            "status", "approved_by_employee_id", "approved_at", "updated_at",
        ])

        EventBus.publish(
            PM.BUDGET_SAVE,
            company_id=company_id,
            payload={
                "budget_id": budget.id,
                "project_id": budget.project_id,
                "status": budget.status,
                "action": "approve",
            },
        )
        return budget


class BudgetItemService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict, instance: BudgetItem | None = None):
        """OP-PM-26 / OP-PM-27 / OP-PM-28."""
        if instance is None:
            instance = BudgetItem(
                company_id=company_id,
                code=data.get("code") or gen_code("BI"),
            )
        for field in (
            "budget_id", "category",
            "planned_amount", "actual_amount", "description",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            PM.BUDGET_ITEM_SAVE,
            company_id=company_id,
            payload={
                "budget_item_id": instance.id,
                "budget_id": instance.budget_id,
                "category": instance.category,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def update_actual(*, company_id: int, budget_item_id: int, actual_amount):
        """OP-PM-28: обновление фактической суммы."""
        item = BudgetItem.objects.select_for_update().get(
            pk=budget_item_id, company_id=company_id,
        )
        item.actual_amount = actual_amount
        item.save(update_fields=["actual_amount", "updated_at"])

        EventBus.publish(
            PM.BUDGET_ITEM_SAVE,
            company_id=company_id,
            payload={
                "budget_item_id": item.id,
                "action": "update_actual",
            },
        )
        return item