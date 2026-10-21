"""
Основные операции с контрагентом и его дочерними сущностями.
OP-CP-05…17.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from core.event_bus import EventBus
from core.events import CPEvents as CP

from apps.cp.models import (
    Address, BankAccount, ContactPerson, Counterparty,
)
from apps.cp.services.helpers import gen_code


class CounterpartyService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: Counterparty | None = None,
             actor_employee_id: int | None = None):
        """
        OP-CP-05 / OP-CP-06.
        Создаёт или обновляет карточку контрагента.
        """
        if instance is None:
            instance = Counterparty(
                company_id=company_id,
                code=data.get("code") or gen_code("CP"),
                created_by_employee_id=actor_employee_id,
            )
        for field in (
            "internal_code", "counterparty_type_id", "category_id",
            "name", "short_name",
            "tax_id", "tax_registration_id", "vat_registration",
            "legal_address", "actual_address",
            "phone", "email", "website", "industry",
            "credit_limit", "payment_terms", "delivery_terms",
            "responsible_employee_id",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        EventBus.publish(
            CP.COUNTERPARTY_SAVE,
            company_id=company_id,
            payload={
                "counterparty_id": instance.id,
                "code": instance.code,
                "name": instance.name,
                "counterparty_type_id": instance.counterparty_type_id,
                "action": "update" if instance.pk and instance.updated_at else "insert",
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def update_status(*, company_id: int, counterparty_id: int,
                      new_status: str):
        """OP-CP-07: изменение статуса."""
        if new_status not in dict(Counterparty.STATUS_CHOICES):
            raise ValueError(_("Недопустимый статус: %s") % new_status)

        cp = Counterparty.objects.select_for_update().get(
            pk=counterparty_id, company_id=company_id,
        )
        old_status = cp.status
        cp.status = new_status
        if new_status == "blacklisted":
            cp.is_blacklisted = True
        elif new_status != "blocked":
            cp.is_blacklisted = False
        cp.save(update_fields=["status", "is_blacklisted", "updated_at"])

        EventBus.publish(
            CP.COUNTERPARTY_UPDATE_STATUS,
            company_id=company_id,
            payload={
                "counterparty_id": cp.id,
                "old_status": old_status,
                "new_status": new_status,
            },
        )
        return cp

    @staticmethod
    @transaction.atomic
    def assign_responsible(*, company_id: int, counterparty_id: int,
                           employee_id: int):
        """OP-CP-08."""
        cp = Counterparty.objects.select_for_update().get(
            pk=counterparty_id, company_id=company_id,
        )
        old = cp.responsible_employee_id
        cp.responsible_employee_id = employee_id
        cp.save(update_fields=["responsible_employee_id", "updated_at"])

        EventBus.publish(
            CP.COUNTERPARTY_ASSIGN_RESPONSIBLE,
            company_id=company_id,
            payload={
                "counterparty_id": cp.id,
                "old_responsible_employee_id": old,
                "new_responsible_employee_id": employee_id,
            },
        )
        return cp


class ContactPersonService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: ContactPerson | None = None):
        """OP-CP-09 / OP-CP-10."""
        if instance is None:
            instance = ContactPerson(
                company_id=company_id,
                code=data.get("code") or gen_code("CONT"),
            )
        for field in (
            "counterparty_id", "natural_person_id",
            "first_name", "last_name", "middle_name",
            "position", "department",
            "phone", "mobile_phone", "email",
            "is_primary", "is_active",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        # Гарантия «одного основного»: если is_primary=True,
        # снимаем флаг с других контактов этого контрагента.
        if instance.is_primary:
            ContactPerson.objects.filter(
                counterparty_id=instance.counterparty_id,
                is_primary=True,
            ).exclude(pk=instance.pk).update(is_primary=False)

        EventBus.publish(
            CP.CONTACT_PERSON_SAVE,
            company_id=company_id,
            payload={
                "contact_id": instance.id,
                "counterparty_id": instance.counterparty_id,
                "action": "save",
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, contact_id: int):
        """OP-CP-11: физическое удаление контакта."""
        contact = ContactPerson.objects.get(
            pk=contact_id, company_id=company_id,
        )
        counterparty_id = contact.counterparty_id
        contact.delete()

        EventBus.publish(
            CP.CONTACT_PERSON_DELETE,
            company_id=company_id,
            payload={
                "contact_id": contact_id,
                "counterparty_id": counterparty_id,
            },
        )


class BankAccountService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: BankAccount | None = None):
        """OP-CP-12 / OP-CP-13."""
        if instance is None:
            instance = BankAccount(
                company_id=company_id,
                code=data.get("code") or gen_code("BA"),
            )
        for field in (
            "counterparty_id", "bank_name", "bank_code",
            "account_number", "currency_id",
            "is_primary", "is_active",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        if instance.is_primary:
            BankAccount.objects.filter(
                counterparty_id=instance.counterparty_id,
                is_primary=True,
            ).exclude(pk=instance.pk).update(is_primary=False)

        EventBus.publish(
            CP.BANK_ACCOUNT_SAVE,
            company_id=company_id,
            payload={
                "bank_account_id": instance.id,
                "counterparty_id": instance.counterparty_id,
                "action": "save",
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, bank_account_id: int):
        """OP-CP-14."""
        acc = BankAccount.objects.get(pk=bank_account_id, company_id=company_id)
        counterparty_id = acc.counterparty_id
        acc.delete()

        EventBus.publish(
            CP.BANK_ACCOUNT_DELETE,
            company_id=company_id,
            payload={"bank_account_id": bank_account_id, "counterparty_id": counterparty_id},
        )


class AddressService:

    @staticmethod
    @transaction.atomic
    def save(*, company_id: int, data: dict,
             instance: Address | None = None):
        """OP-CP-15 / OP-CP-16."""
        if instance is None:
            instance = Address(
                company_id=company_id,
                code=data.get("code") or gen_code("ADDR"),
            )
        for field in (
            "counterparty_id", "address_type",
            "address_line1", "address_line2",
            "city", "region", "postal_code", "country_id",
            "is_primary", "is_active",
        ):
            if field in data:
                setattr(instance, field, data[field])
        instance.save()

        if instance.is_primary:
            Address.objects.filter(
                counterparty_id=instance.counterparty_id,
                is_primary=True,
            ).exclude(pk=instance.pk).update(is_primary=False)

        EventBus.publish(
            CP.ADDRESS_SAVE,
            company_id=company_id,
            payload={
                "address_id": instance.id,
                "counterparty_id": instance.counterparty_id,
                "action": "save",
            },
        )
        return instance

    @staticmethod
    @transaction.atomic
    def delete(*, company_id: int, address_id: int):
        """OP-CP-17."""
        addr = Address.objects.get(pk=address_id, company_id=company_id)
        counterparty_id = addr.counterparty_id
        addr.delete()

        EventBus.publish(
            CP.ADDRESS_DELETE,
            company_id=company_id,
            payload={"address_id": address_id, "counterparty_id": counterparty_id},
        )