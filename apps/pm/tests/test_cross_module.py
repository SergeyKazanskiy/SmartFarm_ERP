"""
Cross-module: CP.blacklist.add → PM ставит проекты на hold.
"""
import pytest
from django.core.management import call_command

from apps.cp.services import BlacklistService
from apps.pm.models import Project


@pytest.mark.django_db
def test_blacklist_puts_projects_on_hold(company, customer, project):
    project.status = "active"
    project.save()

    BlacklistService.add(
        company_id=company.id,
        counterparty_id=customer.id,
        reason="test",
    )
    call_command("process_events", "--once")

    project.refresh_from_db()
    assert project.status == "on_hold"