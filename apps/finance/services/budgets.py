"""
Бюджеты (OP-FIN-07…10).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import FinanceEvents as FE

from apps.finance.models import Budget, BudgetItem
from apps.finance.services.helpers import gen_code


class BudgetService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-07."""
        budget = Budget.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("BUD"),
            financial_project_id=data.get("financial_project_id"),
            period_from=data["period_from"],
            period_to=data["period_to"],
            status="draft",
        )
        EventBus.publish(
            FE.BUDGET_CREATE,
            company_id=company_id,
            payload={"budget_id": budget.id, "status": budget.status},
        )
        return budget

    @staticmethod
    @transaction.atomic
    def approve(*, company_id: int, budget_id: int, approver_employee_id: int):
        """OP-FIN-08."""
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
            FE.BUDGET_APPROVE,
            company_id=company_id,
            payload={
                "budget_id": budget.id,
                "financial_project_id": budget.financial_project_id,
            },
        )
        return budget


class BudgetItemService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-FIN-09."""
        item = BudgetItem.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("BI"),
            budget_id=data["budget_id"],
            cost_center_id=data.get("cost_center_id"),
            planned_amount=data["planned_amount"],
        )
        EventBus.publish(
            FE.BUDGET_ITEM_CREATE,
            company_id=company_id,
            payload={"budget_item_id": item.id, "budget_id": item.budget_id},
        )
        return item

    @staticmethod
    @transaction.atomic
    def update_planned(*, company_id: int, budget_item_id: int, planned_amount):
        """OP-FIN-10."""
        item = BudgetItem.objects.select_for_update().get(
            pk=budget_item_id, company_id=company_id,
        )
        item.planned_amount = planned_amount
        item.save(update_fields=["planned_amount", "updated_at"])
        EventBus.publish(
            FE.BUDGET_ITEM_UPDATE,
            company_id=company_id,
            payload={"budget_item_id": item.id},
        )
        return item