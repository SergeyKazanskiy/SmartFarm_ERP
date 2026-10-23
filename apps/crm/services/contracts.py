"""
Договоры CRM (OP-CRM-23…27).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import CRMEvents as CRM

from apps.crm.models import Contract
from apps.crm.services.helpers import gen_code


class ContractService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-CRM-23: создание (draft)."""
        contract = Contract.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("CONTR"),
            counterparty_id=data["counterparty_id"],
            contract_number=data.get("contract_number", ""),
            contract_date=data.get("contract_date"),
            contract_amount=data.get("contract_amount"),
            status="draft",
            covered_objects_json=data.get("covered_objects_json", []),
        )
        EventBus.publish(
            CRM.CONTRACT_CREATE,
            company_id=company_id,
            payload={
                "contract_id": contract.id,
                "counterparty_id": contract.counterparty_id,
                "contract_amount": float(contract.contract_amount) if contract.contract_amount else None,
            },
        )
        return contract

    @staticmethod
    @transaction.atomic
    def activate(*, company_id: int, contract_id: int):
        """OP-CRM-24."""
        c = Contract.objects.select_for_update().get(
            pk=contract_id, company_id=company_id,
        )
        if c.status != "draft":
            raise ValueError(_("Активировать можно только черновик"))
        c.status = "active"
        c.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            CRM.CONTRACT_ACTIVATE,
            company_id=company_id,
            payload={"contract_id": c.id},
        )
        return c

    @staticmethod
    @transaction.atomic
    def complete(*, company_id: int, contract_id: int):
        """OP-CRM-25."""
        c = Contract.objects.select_for_update().get(
            pk=contract_id, company_id=company_id,
        )
        if c.status != "active":
            raise ValueError(_("Завершить можно только активный договор"))
        c.status = "completed"
        c.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            CRM.CONTRACT_COMPLETE,
            company_id=company_id,
            payload={"contract_id": c.id},
        )
        return c

    @staticmethod
    @transaction.atomic
    def terminate(*, company_id: int, contract_id: int):
        """OP-CRM-26."""
        c = Contract.objects.select_for_update().get(
            pk=contract_id, company_id=company_id,
        )
        if c.status != "active":
            raise ValueError(_("Расторгнуть можно только активный договор"))
        c.status = "terminated"
        c.save(update_fields=["status", "updated_at"])

        EventBus.publish(
            CRM.CONTRACT_TERMINATE,
            company_id=company_id,
            payload={"contract_id": c.id},
        )
        return c

    @staticmethod
    @transaction.atomic
    def update_covered_objects(*, company_id: int, contract_id: int,
                                covered_objects_json: list):
        """OP-CRM-27."""
        c = Contract.objects.select_for_update().get(
            pk=contract_id, company_id=company_id,
        )
        c.covered_objects_json = covered_objects_json
        c.save(update_fields=["covered_objects_json", "updated_at"])

        EventBus.publish(
            CRM.CONTRACT_UPDATE_COVERED_OBJECTS,
            company_id=company_id,
            payload={
                "contract_id": c.id,
                "covered_objects_json": covered_objects_json,
            },
        )
        return c