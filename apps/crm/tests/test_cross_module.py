"""
Cross-module: CP.blacklist.add → CRM проигрывает открытые сделки.
"""
import pytest
from django.core.management import call_command

from apps.cp.services import BlacklistService
from apps.crm.models import Opportunity


@pytest.mark.django_db
def test_blacklist_loses_opportunities(company, counterparty, lead, opportunity):
    # Привязываем лид к контрагенту
    lead.counterparty_id = counterparty.id
    lead.save()

    assert opportunity.is_won is None

    BlacklistService.add(
        company_id=company.id,
        counterparty_id=counterparty.id,
        reason="test",
    )

    # Прогоняем воркер — событие CP.blacklist.add должно дойти до CRM
    call_command("process_events", "--once")

    opportunity.refresh_from_db()
    assert opportunity.is_won == 0
    assert "чёрном списке" in opportunity.lost_reason.lower()