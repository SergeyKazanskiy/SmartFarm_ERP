"""
Производственные заказы (OP-PROD-20…26) и наряды (OP-PROD-27…34).
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import ProductionEvents as PRE

from apps.production.models import ProductionOrder, WorkOrder
from apps.production.services.helpers import gen_code, validate_json_list


class ProductionOrderService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-20."""
        order = ProductionOrder.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("PROD"),
            bom_id=data.get("bom_id"),
            routing_id=data.get("routing_id"),
            planned_quantity=data["planned_quantity"],
            planned_start_date=data.get("planned_start_date"),
            planned_end_date=data.get("planned_end_date"),
            status="draft",
        )
        EventBus.publish(
            PRE.PRODUCTION_ORDER_CREATE,
            company_id=company_id,
            payload={
                "production_order_id": order.id,
                "bom_id": order.bom_id,
                "planned_quantity": float(order.planned_quantity),
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def confirm(*, company_id: int, production_order_id: int):
        """OP-PROD-21. draft → confirmed."""
        order = ProductionOrder.objects.select_for_update().get(
            pk=production_order_id, company_id=company_id,
        )
        if order.status != "draft":
            raise ValueError(_("Подтвердить можно только черновик"))

        order.status = "confirmed"
        order.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.PRODUCTION_ORDER_CONFIRM,
            company_id=company_id,
            payload={
                "production_order_id": order.id,
                "bom_id": order.bom_id,
                "planned_quantity": float(order.planned_quantity),
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def update_plan(*, company_id: int, production_order_id: int, data: dict):
        """OP-PROD-22."""
        order = ProductionOrder.objects.select_for_update().get(
            pk=production_order_id, company_id=company_id,
        )
        if order.status not in ("draft", "confirmed"):
            raise ValueError(_("Редактировать можно только draft/confirmed"))

        for field in ("planned_quantity", "planned_start_date", "planned_end_date"):
            if field in data:
                setattr(order, field, data[field])
        order.save()

        EventBus.publish(
            PRE.PRODUCTION_ORDER_UPDATE_PLAN,
            company_id=company_id,
            payload={"production_order_id": order.id},
        )
        return order

    @staticmethod
    @transaction.atomic
    def update_bom_routing(
        *, company_id: int, production_order_id: int, data: dict,
    ):
        """OP-PROD-23."""
        order = ProductionOrder.objects.select_for_update().get(
            pk=production_order_id, company_id=company_id,
        )
        if order.status not in ("draft", "confirmed"):
            raise ValueError(_("Редактировать можно только draft/confirmed"))

        for field in ("bom_id", "routing_id"):
            if field in data:
                setattr(order, field, data[field])
        order.save()

        EventBus.publish(
            PRE.PRODUCTION_ORDER_UPDATE_BOM_ROUTING,
            company_id=company_id,
            payload={"production_order_id": order.id},
        )
        return order

    @staticmethod
    @transaction.atomic
    def mark_in_progress(*, company_id: int, production_order_id: int):
        """
        OP-PROD-24. Вызывается автоматически из WorkOrderService.start()
        при первом запущенном наряде. Ручной вызов тоже допустим.
        """
        order = ProductionOrder.objects.select_for_update().get(
            pk=production_order_id, company_id=company_id,
        )
        if order.status != "confirmed":
            return order

        order.status = "in_progress"
        order.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.PRODUCTION_ORDER_START,
            company_id=company_id,
            payload={"production_order_id": order.id},
        )
        return order

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, production_order_id: int):
        """OP-PROD-25."""
        order = ProductionOrder.objects.select_for_update().get(
            pk=production_order_id, company_id=company_id,
        )
        if order.status not in ("in_progress", "confirmed"):
            raise ValueError(
                _("Закрыть можно только in_progress/confirmed")
            )

        # Проверка: все наряды завершены/отменены
        active = order.work_orders.exclude(
            status__in=["completed", "cancelled"],
        ).exists()
        if active:
            raise ValueError(
                _("Нельзя закрыть заказ: есть незавершённые наряды")
            )

        order.status = "completed"
        order.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.PRODUCTION_ORDER_COMPLETE,
            company_id=company_id,
            payload={
                "production_order_id": order.id,
                "bom_id": order.bom_id,
                "planned_quantity": float(order.planned_quantity),
            },
        )
        return order

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, production_order_id: int, reason: str = ""):
        """OP-PROD-26."""
        order = ProductionOrder.objects.select_for_update().get(
            pk=production_order_id, company_id=company_id,
        )
        if order.status not in ("draft", "confirmed"):
            raise ValueError(_("Отменить можно только draft/confirmed"))

        order.status = "cancelled"
        order.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.PRODUCTION_ORDER_CANCEL,
            company_id=company_id,
            payload={
                "production_order_id": order.id,
                "reason": reason,
            },
        )
        return order


class WorkOrderService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-PROD-27."""
        wo = WorkOrder.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("WO"),
            production_order_id=data["production_order_id"],
            status="planned",
            planned_start=data.get("planned_start"),
            planned_finish=data.get("planned_finish"),
        )
        EventBus.publish(
            PRE.WORK_ORDER_CREATE,
            company_id=company_id,
            payload={
                "work_order_id": wo.id,
                "production_order_id": wo.production_order_id,
            },
        )
        return wo

    @staticmethod
    @transaction.atomic
    def start(*, company_id: int, work_order_id: int):
        """
        OP-PROD-28. planned → in_progress.
        Триггерит ProductionOrderService.mark_in_progress, если это первый
        запущенный наряд (OP-PROD-24).
        """
        wo = WorkOrder.objects.select_for_update().get(
            pk=work_order_id, company_id=company_id,
        )
        if wo.status != "planned":
            raise ValueError(_("Запустить можно только planned"))

        wo.status = "in_progress"
        wo.actual_start = timezone.now()
        wo.save(update_fields=["status", "actual_start", "updated_at"])

        # Автопереход заказа в in_progress
        ProductionOrderService.mark_in_progress(
            company_id=company_id,
            production_order_id=wo.production_order_id,
        )

        EventBus.publish(
            PRE.WORK_ORDER_START,
            company_id=company_id,
            payload={
                "work_order_id": wo.id,
                "production_order_id": wo.production_order_id,
            },
        )
        return wo

    @staticmethod
    @transaction.atomic
    def hold(*, company_id: int, work_order_id: int, reason: str = ""):
        """OP-PROD-29."""
        wo = WorkOrder.objects.select_for_update().get(
            pk=work_order_id, company_id=company_id,
        )
        if wo.status != "in_progress":
            raise ValueError(_("Приостановить можно только in_progress"))

        wo.status = "on_hold"
        wo.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.WORK_ORDER_HOLD,
            company_id=company_id,
            payload={"work_order_id": wo.id, "reason": reason},
        )
        return wo

    @staticmethod
    @transaction.atomic
    def resume(*, company_id: int, work_order_id: int):
        """OP-PROD-30."""
        wo = WorkOrder.objects.select_for_update().get(
            pk=work_order_id, company_id=company_id,
        )
        if wo.status != "on_hold":
            raise ValueError(_("Возобновить можно только on_hold"))

        wo.status = "in_progress"
        wo.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.WORK_ORDER_RESUME,
            company_id=company_id,
            payload={"work_order_id": wo.id},
        )
        return wo

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, work_order_id: int):
        """OP-PROD-31."""
        wo = WorkOrder.objects.select_for_update().get(
            pk=work_order_id, company_id=company_id,
        )
        if wo.status not in ("in_progress", "on_hold"):
            raise ValueError(_("Завершить можно только in_progress/on_hold"))

        wo.status = "completed"
        wo.actual_finish = timezone.now()
        wo.save(update_fields=["status", "actual_finish", "updated_at"])

        EventBus.publish(
            PRE.WORK_ORDER_COMPLETE,
            company_id=company_id,
            payload={
                "work_order_id": wo.id,
                "production_order_id": wo.production_order_id,
            },
        )
        return wo

    @staticmethod
    @transaction.atomic
    def cancel(*, company_id: int, work_order_id: int):
        """OP-PROD-32."""
        wo = WorkOrder.objects.select_for_update().get(
            pk=work_order_id, company_id=company_id,
        )
        if wo.status != "planned":
            raise ValueError(_("Отменить можно только planned"))

        wo.status = "cancelled"
        wo.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            PRE.WORK_ORDER_CANCEL,
            company_id=company_id,
            payload={"work_order_id": wo.id},
        )
        return wo

    @staticmethod
    @transaction.atomic
    def update_schedule(*, company_id: int, work_order_id: int, data: dict):
        """OP-PROD-33."""
        wo = WorkOrder.objects.select_for_update().get(
            pk=work_order_id, company_id=company_id,
        )
        if wo.status not in ("planned", "on_hold"):
            raise ValueError(_("Менять сроки можно только planned/on_hold"))

        for field in ("planned_start", "planned_finish"):
            if field in data:
                setattr(wo, field, data[field])
        wo.save()

        EventBus.publish(
            PRE.WORK_ORDER_UPDATE_SCHEDULE,
            company_id=company_id,
            payload={"work_order_id": wo.id},
        )
        return wo

    @staticmethod
    @transaction.atomic
    def register_materials(*, company_id: int, work_order_id: int, actual_materials_json: list):
        """OP-PROD-34."""
        wo = WorkOrder.objects.select_for_update().get(
            pk=work_order_id, company_id=company_id,
        )
        wo.actual_materials_json = validate_json_list(
            actual_materials_json, "actual_materials_json",
        )
        wo.save(update_fields=["actual_materials_json", "updated_at"])

        EventBus.publish(
            PRE.WORK_ORDER_REGISTER_MATERIALS,
            company_id=company_id,
            payload={"work_order_id": wo.id},
        )
        return wo