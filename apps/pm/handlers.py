"""
Подписчики PM-модуля на события других модулей.

Реализовано:
- CP.blacklist.add → приостановить все активные проекты с этим заказчиком.

Заглушки:
- APS.plan.conflict → эскалация риска (APS ещё не готов).
- Task.task.complete → синхронизация прогресса PM-задачи (TASK ещё не связан с PM).
"""
import logging

from django.db import transaction

from core.event_bus import DomainEvent, EventBus

from apps.pm.models import Project

logger = logging.getLogger(__name__)


@EventBus.subscribe("CP.blacklist.add")
@transaction.atomic
def on_cp_blacklist_add(event: DomainEvent) -> None:
    """
    Контрагент-заказчик попал в чёрный список:
    все его активные проекты ставим на hold.
    См. CP_Scenarios.yml, SCENARIO-CP-002.
    """
    counterparty_id = event.payload.get("counterparty_id")
    if not counterparty_id:
        return

    affected = Project.objects.filter(
        company_id=event.company_id,
        customer_id=counterparty_id,
        status="active",
    ).update(status="on_hold")

    logger.info(
        "PM: blacklisted customer %s → %d projects on_hold",
        counterparty_id, affected,
    )


# ============================================================
# Заглушки для будущих модулей
# ============================================================

# @EventBus.subscribe("APS.plan.conflict")
# def on_aps_plan_conflict(event: DomainEvent) -> None:
#     """APS не смог распределить ресурсы → создаём риск в проекте."""
#     ...

# @EventBus.subscribe("Task.task.complete")
# def on_task_task_complete(event: DomainEvent) -> None:
#     """Задача TASK завершена → обновить прогресс PM-задачи."""
#     ...