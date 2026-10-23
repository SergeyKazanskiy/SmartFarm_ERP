"""
Лиды (OP-CRM-01…04) и контакты (OP-CRM-05…06).
"""
from __future__ import annotations

from django.db import transaction
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import CRMEvents as CRM

from apps.crm.models import Contact, Lead
from apps.crm.services.helpers import gen_code


class LeadService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict, actor_employee_id: int | None = None):
        """OP-CRM-01: создание лида."""
        lead = Lead.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("LEAD"),
            lead_source_id=data.get("lead_source_id"),
            lead_status_id=data.get("lead_status_id"),
            counterparty_id=data.get("counterparty_id"),
            responsible_employee_id=(
                data.get("responsible_employee_id") or actor_employee_id
            ),
            title=data.get("title", ""),
            description=data.get("description", ""),
            contact_name=data.get("contact_name", ""),
            contact_phone=data.get("contact_phone", ""),
            contact_email=data.get("contact_email", ""),
        )

        EventBus.publish(
            CRM.LEAD_CREATE,
            company_id=company_id,
            payload={
                "lead_id": lead.id,
                "code": lead.code,
                "lead_status_id": lead.lead_status_id,
                "responsible_employee_id": lead.responsible_employee_id,
            },
        )
        return lead

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, lead_id: int, data: dict):
        """Общее обновление (титул, контакты, описание)."""
        lead = Lead.objects.select_for_update().get(
            pk=lead_id, company_id=company_id,
        )
        for field in (
            "title", "description", "contact_name",
            "contact_phone", "contact_email", "lead_source_id",
        ):
            if field in data:
                setattr(lead, field, data[field])
        lead.save()
        return lead

    @staticmethod
    @transaction.atomic
    def assign(*, company_id: int, lead_id: int, employee_id: int):
        """OP-CRM-02: назначение ответственного."""
        lead = Lead.objects.select_for_update().get(
            pk=lead_id, company_id=company_id,
        )
        old = lead.responsible_employee_id
        lead.responsible_employee_id = employee_id
        lead.save(update_fields=["responsible_employee_id", "updated_at"])

        EventBus.publish(
            CRM.LEAD_ASSIGN,
            company_id=company_id,
            payload={
                "lead_id": lead.id,
                "old_responsible_employee_id": old,
                "new_responsible_employee_id": employee_id,
            },
        )
        return lead

    @staticmethod
    @transaction.atomic
    def update_status(*, company_id: int, lead_id: int, new_status_id: int):
        """OP-CRM-03."""
        lead = Lead.objects.select_for_update().get(
            pk=lead_id, company_id=company_id,
        )
        old = lead.lead_status_id
        lead.lead_status_id = new_status_id
        lead.save(update_fields=["lead_status", "updated_at"])

        EventBus.publish(
            CRM.LEAD_UPDATE_STATUS,
            company_id=company_id,
            payload={
                "lead_id": lead.id,
                "old_lead_status_id": old,
                "new_lead_status_id": new_status_id,
            },
        )
        return lead

    @staticmethod
    @transaction.atomic
    def link_counterparty(*, company_id: int, lead_id: int, counterparty_id: int):
        """OP-CRM-04: связывание с контрагентом (CP)."""
        lead = Lead.objects.select_for_update().get(
            pk=lead_id, company_id=company_id,
        )
        lead.counterparty_id = counterparty_id
        lead.save(update_fields=["counterparty_id", "updated_at"])

        EventBus.publish(
            CRM.LEAD_LINK_COUNTERPARTY,
            company_id=company_id,
            payload={
                "lead_id": lead.id,
                "counterparty_id": counterparty_id,
            },
        )
        return lead


class ContactService:

    @staticmethod
    @transaction.atomic
    def create(*, company_id: int, data: dict):
        """OP-CRM-05."""
        contact = Contact.objects.create(
            company_id=company_id,
            code=data.get("code") or gen_code("CONT"),
            natural_person_id=data.get("natural_person_id"),
            counterparty_id=data.get("counterparty_id"),
            position=data.get("position", ""),
            phone=data.get("phone", ""),
            email=data.get("email", ""),
        )
        EventBus.publish(
            CRM.CONTACT_CREATE,
            company_id=company_id,
            payload={
                "contact_id": contact.id,
                "counterparty_id": contact.counterparty_id,
            },
        )
        return contact

    @staticmethod
    @transaction.atomic
    def update(*, company_id: int, contact_id: int, data: dict):
        """OP-CRM-06."""
        contact = Contact.objects.select_for_update().get(
            pk=contact_id, company_id=company_id,
        )
        for field in ("position", "phone", "email", "natural_person_id"):
            if field in data:
                setattr(contact, field, data[field])
        contact.save()

        EventBus.publish(
            CRM.CONTACT_UPDATE,
            company_id=company_id,
            payload={"contact_id": contact.id},
        )
        return contact