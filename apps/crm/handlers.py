"""
Подписчики CRM-модуля на события других модулей.

Сейчас реализовано:
- CP.blacklist.add → проиграть открытые сделки контрагента + отказ лидов.

TODO (после Sales, Finance):
- SALES.order.shipped → обновить прогресс по договору.
- FIN.invoice.paid → логировать оплату контрагенту.
"""
import logging

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import DomainEvent, EventBus

from apps.crm.models import Lead, Opportunity

logger = logging.getLogger(__name__)


@EventBus.subscribe("CP.blacklist.add")
@transaction.atomic
def on_cp_blacklist_add(event: DomainEvent) -> None:
    """
    Контрагент попал в чёрный список CP:
    - все открытые сделки помечаем как проигранные (is_won=0);
    - все открытые лиды переводим в статус «Отказ».

    См. CP_Scenarios.yml, SCENARIO-CP-002.
    """
    counterparty_id = event.payload.get("counterparty_id")
    if not counterparty_id:
        return

    lost_reason = _("Контрагент в чёрном списке")

    lost_opportunities = Opportunity.objects.filter(
        company_id=event.company_id,
        is_won__isnull=True,
        lead__counterparty_id=counterparty_id,
    ).update(is_won=0, lost_reason=lost_reason)

    logger.info(
        "CRM: blacklisted counterparty %s → %d opportunities lost",
        counterparty_id, lost_opportunities,
    )


@EventBus.subscribe("CP.counterparty.save")
def on_cp_counterparty_save(event: DomainEvent) -> None:
    """
    Логируем сохранение контрагента из CP. Заготовка под будущую
    синхронизацию (например, денормализовать имя контрагента в лиды).
    """
    logger.debug(
        "CRM: получено событие CP.counterparty.save для CP id=%s",
        event.payload.get("counterparty_id"),
    )