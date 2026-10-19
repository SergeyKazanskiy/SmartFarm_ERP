"""
Воркер Event Bus. Запускается отдельным процессом:

    python manage.py process_events

или в cron:

    * * * * * cd /app && python manage.py process_events --once
"""
import logging
import time

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.event_bus import DomainEvent, EventBus

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
POLL_INTERVAL = 5  # секунд


class Command(BaseCommand):
    help = "Обрабатывает события из очереди DomainEvent"

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Обработать все pending-события и выйти (для cron)",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=BATCH_SIZE,
        )

    def handle(self, *args, **options):
        once = options["once"]
        batch_size = options["batch_size"]

        self.stdout.write(self.style.SUCCESS("Event worker started"))
        while True:
            processed = self._process_batch(batch_size)
            if once and processed == 0:
                break
            if not once:
                time.sleep(POLL_INTERVAL)
            if once and processed > 0:
                continue

    def _process_batch(self, batch_size: int) -> int:
        # Транзакция + select_for_update(skip_locked=True) гарантируют,
        # что параллельные воркеры не возьмут одно и то же событие.
        with transaction.atomic():
            events = list(
                DomainEvent.objects
                .select_for_update(skip_locked=True)
                .filter(status=DomainEvent.STATUS_PENDING)
                .order_by("created_at")[:batch_size]
            )

            for event in events:
                try:
                    EventBus.dispatch(event)
                    event.status = DomainEvent.STATUS_PROCESSED
                    event.processed_at = timezone.now()
                    event.error = ""
                except Exception as exc:
                    event.attempts += 1
                    event.error = str(exc)[:2000]
                    event.status = DomainEvent.STATUS_FAILED
                    logger.exception("Event %s failed: %s", event.id, exc)
                event.save(update_fields=[
                    "status", "processed_at", "error", "attempts",
                ])

        return len(events)