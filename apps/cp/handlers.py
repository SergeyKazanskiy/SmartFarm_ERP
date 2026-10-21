"""
Подписчики CP-модуля на события других модулей.
На момент Части 2 ничего не слушаем — Sales, Procurement, Finance ещё не готовы.
Заглушки оставлены, чтобы было куда добавлять.
"""
import logging

from core.event_bus import EventBus, DomainEvent

logger = logging.getLogger(__name__)


# ============================================================
# TODO: слушатели из будущих модулей
# ============================================================

# @EventBus.subscribe("FIN.invoice.overdue")
# def on_invoice_overdue(event: DomainEvent) -> None:
#     """
#     Просрочка оплаты → снижаем рейтинг контрагента.
#     См. CP_Scenarios.yml, SCENARIO-CP-006.
#     """
#     ...

# @EventBus.subscribe("SALES.order.cancelled")
# def on_sales_order_cancelled(event: DomainEvent) -> None:
#     ...

# ============================================================
# Слушатели для внутренней логики CP
# ============================================================

@EventBus.subscribe("CP.blacklist.add")
def on_blacklist_added(event: DomainEvent) -> None:
    """
    При добавлении в чёрный список — логируем и (TODO) рассылаем
    уведомления ответственным подразделениям (Sales, Procurement).
    """
    logger.info(
        "CP: контрагент %s добавлен в чёрный список (company=%s)",
        event.payload.get("counterparty_id"), event.company_id,
    )