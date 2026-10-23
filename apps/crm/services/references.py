"""
Справочники CRM: источники, статусы, стадии, типы активностей, воронки.
Все справочники — простые CRUD-сервисы с публикацией события save.
"""
from __future__ import annotations

from django.db import transaction

from core.event_bus import EventBus

from apps.crm.models import (
    ActivityType, LeadSource, LeadStatus, OpportunityStage, SalesFunnel,
)
from apps.crm.services.helpers import gen_code


class _BaseReferenceService:
    """Универсальный save для справочников."""

    MODEL = None
    EVENT = None

    @classmethod
    @transaction.atomic
    def save(cls, *, company_id: int, data: dict, instance=None):
        if instance is None:
            instance = cls.MODEL(
                company_id=company_id,
                code=data.get("code") or gen_code(cls.MODEL.__name__[:4].upper()),
            )
        for field in ("name", "is_active", "stages_json"):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        if cls.EVENT:
            EventBus.publish(
                cls.EVENT,
                company_id=company_id,
                payload={"id": instance.id, "code": instance.code},
            )
        return instance


class LeadSourceService(_BaseReferenceService):
    MODEL = LeadSource
    EVENT = None


class LeadStatusService(_BaseReferenceService):
    MODEL = LeadStatus
    EVENT = None


class OpportunityStageService(_BaseReferenceService):
    MODEL = OpportunityStage
    EVENT = None


class ActivityTypeService(_BaseReferenceService):
    MODEL = ActivityType
    EVENT = None


class SalesFunnelService(_BaseReferenceService):
    MODEL = SalesFunnel
    EVENT = None