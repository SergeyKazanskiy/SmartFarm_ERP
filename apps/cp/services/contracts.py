"""
Договоры (OP-CP-21…25) и прикреплённые документы (OP-CP-28…29).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import CPEvents as CP

from apps.cp.models import Attachment, Contract
from apps.cp.services.helpers import gen_code


class ContractService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: Contract | None = None,
             actor_employee_id: int | None = None):
        """OP-CP-21 / OP-CP-22."""
        if instance is None:
            instance = Contract(
                company_id=company_id,
                code=data.get("code") or gen_code("CONTR"),
                status="draft",
                created_by_employee_id=actor_employee_id,
            )
        for field in (
            "counterparty_id", "contract_number", "contract_date",
            "valid_from", "valid_to", "contract_type",
            "amount", "currency_id",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            CP.CONTRACT_SAVE,
            company_id=company_id,
            payload={
                "contract_id": instance.id,
                "counterparty_id": instance.counterparty_id,
                "status": instance.status,
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def activate(*, company_id: int, contract_id: int):
        """OP-CP-23."""
        contract = Contract.objects.select_for_update().get(
            pk=contract_id, company_id=company_id,
        )
        if contract.status != "draft":
            raise ValueError(_("Активировать можно только договор в статусе 'draft'"))
        contract.status = "active"
        contract.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            CP.CONTRACT_ACTIVATE,
            company_id=company_id,
            payload={"contract_id": contract.id},
        )
        return contract

    @staticmethod
    @transaction.atomic
    def terminate(*, company_id: int, contract_id: int):
        """OP-CP-24."""
        contract = Contract.objects.select_for_update().get(
            pk=contract_id, company_id=company_id,
        )
        if contract.status != "active":
            raise ValueError(_("Расторгнуть можно только активный договор"))
        contract.status = "terminated"
        contract.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            CP.CONTRACT_TERMINATE,
            company_id=company_id,
            payload={"contract_id": contract.id},
        )
        return contract

    @staticmethod
    @transaction.atomic
    def expire_due() -> int:
        """
        OP-CP-25: служебная операция, помечает истёкшие договоры.
        Запускается через management-команду (cron).
        """
        today = timezone_now().date()
        count = Contract.objects.filter(
            status="active", valid_to__lt=today,
        ).update(status="expired")
        return count


class AttachmentService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict, actor_employee_id: int | None = None):
        """OP-CP-28."""
        att = Attachment.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("ATT"),
            counterparty_id=data["counterparty_id"],
            document_id=data["document_id"],
            attachment_type=data.get("attachment_type", ""),
            description=data.get("description", ""),
            created_by_employee_id=actor_employee_id,
        )
        EventBus.publish(
            CP.ATTACHMENT_CREATE,
            company_id=company_id,
            payload={
                "attachment_id": att.id,
                "counterparty_id": att.counterparty_id,
                "document_id": att.document_id,
            },
        )
        return att

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, attachment_id: int):
        """OP-CP-29."""
        att = Attachment.objects.get(pk=attachment_id, company_id=company_id)
        counterparty_id = att.counterparty_id
        att.delete()

        EventBus.publish(
            CP.ATTACHMENT_DELETE,
            company_id=company_id,
            payload={"attachment_id": attachment_id, "counterparty_id": counterparty_id},
        )


# Локальный импорт, чтобы не засорять шапку
from django.utils import timezone as _tz
def timezone_now():
    return _tz.now()