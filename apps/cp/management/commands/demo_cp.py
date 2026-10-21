"""
Демо-команда: загружает CP_test_data.json и прогоняет базовый сценарий.

Использование:
    python manage.py demo_cp --company=1
    python manage.py demo_cp --company=1 --file=apps/cp/workflow/CP_test_data.json
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import CPEvents as CP

from apps.cp.models import (
    Address, Attachment, BankAccount, Blacklist, Category, ContactPerson,
    Contract, Counterparty, CounterpartyType, Interaction, Rating,
)


class Command(BaseCommand):
    help = "Загружает тестовые данные CP и публикует события"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/cp/workflow/CP_test_data.json",
        )
        parser.add_argument(
            "--emit-events", action="store_true", default=True,
            help="Публиковать события CP.counterparty.save (по умолчанию)",
        )

    def handle(self, *args, **options):
        try:
            company = Company.objects.get(pk=options["company"])
        except Company.DoesNotExist:
            raise CommandError(f"Company {options['company']} not found")

        path = Path(options["file"])
        if not path.exists():
            raise CommandError(f"Файл не найден: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tables = data.get("tables", {})
        counters = {}

        with transaction.atomic():
            counters["counterparty_type"] = self._load_references(
                company, tables.get("cp_counterparty_type", []),
                CounterpartyType,
            )
            counters["category"] = self._load_categories(
                company, tables.get("cp_category", []),
            )
            counters["counterparty"] = self._load_counterparties(
                company, tables.get("cp_counterparty", []),
            )
            counters["contact_person"] = self._load_contacts(
                company, tables.get("cp_contact_person", []),
            )
            counters["bank_account"] = self._load_bank_accounts(
                company, tables.get("cp_bank_account", []),
            )
            counters["address"] = self._load_addresses(
                company, tables.get("cp_address", []),
            )
            counters["rating"] = self._load_ratings(
                company, tables.get("cp_rating", []),
            )
            counters["interaction"] = self._load_interactions(
                company, tables.get("cp_interaction", []),
            )
            counters["contract"] = self._load_contracts(
                company, tables.get("cp_contract", []),
            )
            counters["attachment"] = self._load_attachments(
                company, tables.get("cp_attachment", []),
            )
            counters["blacklist"] = self._load_blacklist(
                company, tables.get("cp_blacklist", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные CP загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # ----------------------------------------------------------

    def _load_references(self, company, rows, model) -> int:
        n = 0
        for r in rows:
            model.objects.update_or_create(
                company=company, code=r["counterparty_type_id"],
                defaults={
                    "name": r["counterparty_type_name"],
                    "is_active": r.get("is_active", True),
                },
            )
            n += 1
        return n

    def _load_categories(self, company, rows) -> int:
        # Два прохода: сначала без parent, потом проставляем parent
        n = 0
        objs = {}
        for r in rows:
            obj, _ = Category.objects.update_or_create(
                company=company, code=r["category_id"],
                defaults={
                    "name": r["category_name"],
                    "is_active": r.get("is_active", True),
                },
            )
            objs[r["category_id"]] = obj
            n += 1
        for r in rows:
            if r.get("parent_id"):
                parent = objs.get(r["parent_id"])
                if parent:
                    objs[r["category_id"]].parent = parent
                    objs[r["category_id"]].save(update_fields=["parent"])
        return n

    def _load_counterparties(self, company, rows) -> int:
        n = 0
        for r in rows:
            ctype = CounterpartyType.objects.get(
                company=company, code=r["counterparty_type_id"],
            )
            cat = (
                Category.objects.get(company=company, code=r["category_id"])
                if r.get("category_id") else None
            )
            Counterparty.objects.update_or_create(
                company=company, code=r["counterparty_id"],
                defaults={
                    "counterparty_type": ctype,
                    "category": cat,
                    "internal_code": r.get("code", ""),
                    "name": r["name"],
                    "short_name": r.get("short_name", ""),
                    "tax_id": r.get("tax_id", ""),
                    "tax_registration_id": r.get("tax_registration_id", ""),
                    "vat_registration": r.get("vat_registration", ""),
                    "legal_address": r.get("legal_address", ""),
                    "actual_address": r.get("actual_address", ""),
                    "phone": r.get("phone", ""),
                    "email": r.get("email", ""),
                    "website": r.get("website", ""),
                    "industry": r.get("industry", ""),
                    "credit_limit": r.get("credit_limit"),
                    "payment_terms": r.get("payment_terms", ""),
                    "delivery_terms": r.get("delivery_terms", ""),
                    "status": r.get("status_id", "active"),
                    "is_blacklisted": r.get("is_blacklisted", False),
                    "responsible_employee_id": _parse_emp_id(r.get("responsible_employee_id")),
                    "created_by_employee_id": _parse_emp_id(r.get("created_by_employee_id")),
                },
            )
            n += 1
        return n

    def _load_contacts(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            ContactPerson.objects.update_or_create(
                company=company, code=r["contact_id"],
                defaults={
                    "counterparty": cp,
                    "first_name": r.get("first_name", ""),
                    "last_name": r.get("last_name", ""),
                    "middle_name": r.get("middle_name", ""),
                    "position": r.get("position", ""),
                    "department": r.get("department", ""),
                    "phone": r.get("phone", ""),
                    "mobile_phone": r.get("mobile_phone", ""),
                    "email": r.get("email", ""),
                    "is_primary": r.get("is_primary", False),
                    "is_active": r.get("is_active", True),
                },
            )
            n += 1
        return n

    def _load_bank_accounts(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            BankAccount.objects.update_or_create(
                company=company, code=r["bank_account_id"],
                defaults={
                    "counterparty": cp,
                    "bank_name": r.get("bank_name", ""),
                    "bank_code": r.get("bank_code", ""),
                    "account_number": r["account_number"],
                    "is_primary": r.get("is_primary", False),
                    "is_active": r.get("is_active", True),
                },
            )
            n += 1
        return n

    def _load_addresses(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            Address.objects.update_or_create(
                company=company, code=r["address_id"],
                defaults={
                    "counterparty": cp,
                    "address_type": r.get("address_type", ""),
                    "address_line1": r.get("address_line1", ""),
                    "address_line2": r.get("address_line2", "") or "",
                    "city": r.get("city", ""),
                    "region": r.get("region", ""),
                    "postal_code": r.get("postal_code", ""),
                    "is_primary": r.get("is_primary", False),
                    "is_active": r.get("is_active", True),
                },
            )
            n += 1
        return n

    def _load_ratings(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            Rating.objects.update_or_create(
                company=company,
                counterparty=cp,
                rating_date=r["rating_date"],
                rating_type=r.get("rating_type", "overall"),
                defaults={
                    "rating_value": r["rating_value"],
                    "comment": r.get("comment", ""),
                    "rated_by_employee_id": _parse_emp_id(r.get("rated_by_employee_id")),
                },
            )
            n += 1
        return n

    def _load_interactions(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            contact = None
            if r.get("contact_person_id"):
                contact = ContactPerson.objects.filter(
                    company=company, code=r["contact_person_id"],
                ).first()
            Interaction.objects.update_or_create(
                company=company,
                counterparty=cp,
                interaction_date=r["interaction_date"],
                interaction_type=r["interaction_type"],
                defaults={
                    "contact_person": contact,
                    "employee_id": _parse_emp_id(r.get("employee_id")),
                    "subject": r.get("subject", ""),
                    "description": r.get("description", ""),
                    "result": r.get("result", ""),
                    "next_action_date": r.get("next_action_date"),
                },
            )
            n += 1
        return n

    def _load_contracts(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            Contract.objects.update_or_create(
                company=company, code=r["contract_id"],
                defaults={
                    "counterparty": cp,
                    "contract_number": r.get("contract_number", ""),
                    "contract_date": r.get("contract_date"),
                    "valid_from": r.get("valid_from"),
                    "valid_to": r.get("valid_to"),
                    "contract_type": r.get("contract_type", ""),
                    "amount": r.get("amount"),
                    "status": r.get("status_id", "draft"),
                    "created_by_employee_id": _parse_emp_id(r.get("created_by_employee_id")),
                },
            )
            n += 1
        return n

    def _load_attachments(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            Attachment.objects.update_or_create(
                company=company, code=r["attachment_id"],
                defaults={
                    "counterparty": cp,
                    "document_id": _parse_emp_id(r.get("document_id")) or 0,
                    "attachment_type": r.get("attachment_type", ""),
                    "description": r.get("description", ""),
                    "created_by_employee_id": _parse_emp_id(r.get("created_by_employee_id")),
                },
            )
            n += 1
        return n

    def _load_blacklist(self, company, rows) -> int:
        n = 0
        for r in rows:
            cp = Counterparty.objects.get(company=company, code=r["counterparty_id"])
            Blacklist.objects.update_or_create(
                company=company, counterparty=cp, block_date=r["block_date"],
                defaults={
                    "reason": r.get("reason", ""),
                    "blocked_by_employee_id": _parse_emp_id(r.get("blocked_by_employee_id")),
                    "unblock_date": r.get("unblock_date"),
                    "unblock_reason": r.get("unblock_reason") or "",
                    "unblocked_by_employee_id": _parse_emp_id(r.get("unblocked_by_employee_id")),
                },
            )
            n += 1
        return n

    def _emit_events(self, company) -> None:
        """Публикует по одному событию на каждого контрагента."""
        for cp in Counterparty.objects.filter(company=company):
            EventBus.publish(
                CP.COUNTERPARTY_SAVE,
                company_id=company.id,
                payload={
                    "counterparty_id": cp.id,
                    "code": cp.code,
                    "name": cp.name,
                    "counterparty_type_id": cp.counterparty_type_id,
                    "action": "insert",
                },
            )


def _parse_emp_id(value) -> int | None:
    """'EMP-010' → 10; None → None."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value).replace("EMP-", "").lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None
    

# Ключевые приёмы:

# update_or_create(company=..., code=...) — идемпотентность demo-команды.
# _parse_emp_id("EMP-010") → 10 — конвертация строковых employee_id в BigInteger для внешних ссылок.
# Публикация события одного типа на каждого контрагента (а не на каждую сущность) — этого достаточно для теста workflow.