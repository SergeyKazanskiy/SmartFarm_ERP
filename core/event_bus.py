"""
Event Bus через Outbox Pattern.

publish(event_type, company_id, payload) — только пишет строку в core_domain_event.
Никаких вызовов подписчиков в момент публикации.

dispatch(event) — вызывается воркером (process_events), синхронно дергает всех
подписчиков. Если подписчик падает — событие помечается как failed.

Гарантия: at-least-once. Подписчики должны быть идемпотентными.
"""
import logging

from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class DomainEvent(models.Model):
    """
    Журнал доменных событий (Outbox Pattern).
    Пишется в той же транзакции, что и бизнес-данные.
    """
    STATUS_PENDING = "pending"
    STATUS_PROCESSED = "processed"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_PROCESSED, _("Processed")),
        (STATUS_FAILED, _("Failed")),
    ]

    id = models.BigAutoField(primary_key=True)
    event_type = models.CharField(max_length=128, db_index=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        db_index=True,
    )
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "core_domain_event"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]
        verbose_name = _("Domain event")
        verbose_name_plural = _("Domain events")

    def __str__(self):
        return f"{self.event_type} [{self.status}]"


class EventBus:
    """
    Публикация событий и регистрация подписчиков.
    Использование:

        @EventBus.subscribe("HR.employee.hire")
        def on_hire(event: DomainEvent):
            ...

        EventBus.publish("HR.employee.hire", company_id=1, payload={...})
    """
    _subscribers: dict[str, list] = {}

    @classmethod
    def subscribe(cls, event_type: str):
        """Декоратор для регистрации подписчика."""
        def decorator(func):
            cls._subscribers.setdefault(event_type, []).append(func)
            logger.debug("EventBus: подписчик %s на %s", func.__name__, event_type)
            return func
        return decorator

    @classmethod
    def publish(cls, event_type: str, company_id: int | None, payload: dict) -> DomainEvent:
        """
        Пишет событие в журнал. НЕ вызывает подписчиков.
        Должно вызываться внутри транзакции, где сохраняются бизнес-данные.
        """
        event = DomainEvent.objects.create(
            event_type=event_type,
            company_id=company_id,
            payload=payload,
        )
        logger.info("EventBus: опубликовано %s (id=%s)", event_type, event.id)
        return event

    @classmethod
    def dispatch(cls, event: DomainEvent) -> None:
        """
        Синхронно вызывает всех подписчиков.
        Вызывается воркером, не пользовательским кодом.
        """
        handlers = cls._subscribers.get(event.event_type, [])
        if not handlers:
            logger.debug("EventBus: нет подписчиков на %s", event.event_type)
            return

        for handler in handlers:
            handler(event)