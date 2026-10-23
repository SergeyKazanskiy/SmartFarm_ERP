"""
Подписчики Sales-модуля на события других модулей.

Реализовано:
- CP.blacklist.add → отмена draft/confirmed заказов клиента, чей counterparty
  заблокирован в CP.

Заглушки:
- PM.project.save (интеграция на будущее).
- CRM.opportunity.win → авто-создание Sales.Opportunity (когда свяжем CRM и Sales).
- WMS.* / FIN.* / Production.* → когда появятся эти модули.
"""
import logging

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import DomainEvent, EventBus

from apps.sales.models import Customer, Order

logger = logging.getLogger(__name__)


@EventBus.subscribe("CP.blacklist.add")
@transaction.atomic
def on_cp_blacklist_add(event: DomainEvent) -> None:
    """
    Контрагент попал в чёрный список CP:
    - все заказы клиента в статусе draft/confirmed → cancelled.
    См. CP_Scenarios.yml, SCENARIO-CP-002.
    """
    counterparty_id = event.payload.get("counterparty_id")
    if not counterparty_id:
        return

    affected = Order.objects.filter(
        company_id=event.company_id,
        customer__counterparty_id=counterparty_id,
        status__in=["draft", "confirmed"],
    ).update(status="cancelled")

    logger.info(
        "Sales: blacklisted counterparty %s → %d orders cancelled",
        counterparty_id, affected,
    )


# ============================================================
# Заглушки для будущих модулей
# ============================================================

# @EventBus.subscribe("CRM.opportunity.win")
# def on_crm_opportunity_win(event: DomainEvent) -> None:
#     """Сделка CRM выиграна → создать Sales.Opportunity (или сразу Quote)."""
#     ...

# @EventBus.subscribe("WMS.inventory.out_of_stock")
# def on_wms_out_of_stock(event: DomainEvent) -> None:
#     """Нет товара на складе → пометить заказ как ожидающий."""
#     ...

# @EventBus.subscribe("FIN.invoice.paid")
# def on_fin_invoice_paid(event: DomainEvent) -> None:
#     """FIN подтвердил оплату → Sales.Invoice.status = paid."""
#     ...