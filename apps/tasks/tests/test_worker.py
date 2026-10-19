"""
Тест воркера process_events: обрабатывает pending, помечает processed.
"""
import pytest
from django.core.management import call_command

from core.event_bus import DomainEvent, EventBus
from core.events import HREvents as HR


@pytest.mark.django_db
def test_worker_processes_pending_events(company):
    event = EventBus.publish(
        HR.EMPLOYEE_HIRE, company_id=company.id, payload={"employee_id": 1},
    )
    assert event.status == DomainEvent.STATUS_PENDING

    call_command("process_events", "--once")

    event.refresh_from_db()
    assert event.status == DomainEvent.STATUS_PROCESSED
    assert event.processed_at is not None