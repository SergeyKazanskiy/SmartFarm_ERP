"""
Демо-команда: загружает CRM_test_data.json и публикует события.

Использование:
    python manage.py demo_crm --company=1
    python manage.py demo_crm --company=1 --file=apps/crm/workflow/CRM_test_data.json
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.companies.models import Company
from core.event_bus import EventBus
from core.events import CRMEvents as CRM

from apps.crm.models import (
    Activity, ActivityType, CommercialOffer, CommercialOfferLine,
    Contact, Contract, Lead, LeadSource, LeadStatus,
    Opportunity, OpportunityStage, PriceList, PriceListItem,
)
from apps.cp.models import Counterparty   # для маппинга CP-005 → id


class Command(BaseCommand):
    help = "Загружает тестовые данные CRM и публикует события"

    def add_arguments(self, parser):
        parser.add_argument("--company", type=int, required=True)
        parser.add_argument(
            "--file", type=str,
            default="apps/crm/workflow/CRM_test_data.json",
        )
        parser.add_argument(
            "--emit-events", action="store_true", default=True,
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
            counters["lead_source"] = self._load_references(
                company, tables.get("crm_lead_source", []),
                LeadSource, code_field="lead_source_id", name_field="lead_source_name",
            )
            counters["lead_status"] = self._load_references(
                company, tables.get("crm_lead_status", []),
                LeadStatus, code_field="lead_status_id", name_field="lead_status_name",
            )
            counters["opportunity_stage"] = self._load_references(
                company, tables.get("crm_opportunity_stage", []),
                OpportunityStage, code_field="opportunity_stage_id",
                name_field="opportunity_stage_name",
            )
            counters["activity_type"] = self._load_references(
                company, tables.get("crm_activity_type", []),
                ActivityType, code_field="activity_type_id",
                name_field="activity_type_name",
            )
            counters["contact"] = self._load_contacts(
                company, tables.get("crm_contact", []),
            )
            counters["lead"] = self._load_leads(
                company, tables.get("crm_lead", []),
            )
            counters["opportunity"] = self._load_opportunities(
                company, tables.get("crm_opportunity", []),
            )
            counters["activity"] = self._load_activities(
                company, tables.get("crm_activity", []),
            )
            counters["price_list"] = self._load_price_lists(
                company, tables.get("crm_price_list", []),
            )
            counters["price_list_item"] = self._load_price_list_items(
                company, tables.get("crm_price_list_item", []),
            )
            counters["offer"] = self._load_offers(
                company, tables.get("crm_commercial_offer", []),
            )
            counters["offer_line"] = self._load_offer_lines(
                company, tables.get("crm_commercial_offer_line", []),
            )
            counters["contract"] = self._load_contracts(
                company, tables.get("crm_contract", []),
            )

            if options["emit_events"]:
                self._emit_events(company)

        self.stdout.write(self.style.SUCCESS("Демо-данные CRM загружены:"))
        for k, v in counters.items():
            self.stdout.write(f"  {k}: {v}")
        self.stdout.write(
            "\nНе забудьте запустить: python manage.py process_events --once"
        )

    # ----------------------------------------------------------
    # Загрузчики
    # ----------------------------------------------------------

    def _load_references(self, company, rows, model, code_field, name_field) -> int:
        n = 0
        for r in rows:
            model.objects.update_or_create(
                company=company, code=r[code_field],
                defaults={"name": r[name_field]},
            )
            n += 1
        return n

    def _load_contacts(self, company, rows) -> int:
        n = 0
        for r in rows:
            Contact.objects.update_or_create(
                company=company, code=r["contact_id"],
                defaults={
                    "natural_person_id": _parse_emp_id(r.get("natural_person_id")),
                    "counterparty_id": self._resolve_cp(r.get("counterparty_id"), company),
                    "position": r.get("position", ""),
                    "phone": r.get("phone", ""),
                    "email": r.get("email", ""),
                },
            )
            n += 1
        return n

    def _load_leads(self, company, rows) -> int:
        n = 0
        for r in rows:
            src = LeadSource.objects.filter(
                company=company, code=r.get("lead_source_id"),
            ).first() if r.get("lead_source_id") else None
            stat = LeadStatus.objects.filter(
                company=company, code=r.get("lead_status_id"),
            ).first() if r.get("lead_status_id") else None

            Lead.objects.update_or_create(
                company=company, code=r["lead_id"],
                defaults={
                    "lead_source": src,
                    "lead_status": stat,
                    "counterparty_id": self._resolve_cp(r.get("counterparty_id"), company),
                    "responsible_employee_id": _parse_emp_id(r.get("responsible_employee_id")),
                    "title": r.get("title", f"Lead {r['lead_id']}"),
                },
            )
            n += 1
        return n

    def _load_opportunities(self, company, rows) -> int:
        n = 0
        for r in rows:
            lead = Lead.objects.filter(
                company=company, code=r.get("lead_id"),
            ).first() if r.get("lead_id") else None
            stage = OpportunityStage.objects.filter(
                company=company, code=r.get("opportunity_stage_id"),
            ).first() if r.get("opportunity_stage_id") else None

            Opportunity.objects.update_or_create(
                company=company, code=r["opportunity_id"],
                defaults={
                    "lead": lead,
                    "opportunity_stage": stage,
                    "responsible_employee_id": _parse_emp_id(r.get("responsible_employee_id")),
                    "title": r.get("title", f"Opportunity {r['opportunity_id']}"),
                    "amount": r.get("amount"),
                    "expected_close_date": r.get("expected_close_date"),
                    "is_won": r.get("is_won"),
                    "lost_reason": r.get("lost_reason") or "",
                },
            )
            n += 1
        return n

    def _load_activities(self, company, rows) -> int:
        n = 0
        for r in rows:
            at = ActivityType.objects.filter(
                company=company, code=r.get("activity_type_id"),
            ).first() if r.get("activity_type_id") else None
            lead = Lead.objects.filter(
                company=company, code=r.get("lead_id"),
            ).first() if r.get("lead_id") else None
            opp = Opportunity.objects.filter(
                company=company, code=r.get("opportunity_id"),
            ).first() if r.get("opportunity_id") else None

            Activity.objects.update_or_create(
                company=company, code=r["activity_id"],
                defaults={
                    "activity_type": at,
                    "lead": lead,
                    "opportunity": opp,
                    "employee_id": _parse_emp_id(r.get("employee_id")),
                    "activity_date": r.get("activity_date"),
                    "is_completed": bool(r.get("is_completed")),
                    "result": r.get("result") or "",
                },
            )
            n += 1
        return n

    def _load_price_lists(self, company, rows) -> int:
        n = 0
        for r in rows:
            PriceList.objects.update_or_create(
                company=company, code=r["price_list_id"],
                defaults={
                    "name": r["price_list_name"],
                    "valid_from": r.get("valid_from"),
                },
            )
            n += 1
        return n

    def _load_price_list_items(self, company, rows) -> int:
        n = 0
        for r in rows:
            pl = PriceList.objects.get(
                company=company, code=r["price_list_id"],
            )
            PriceListItem.objects.update_or_create(
                company=company, code=r["price_list_item_id"],
                defaults={
                    "price_list": pl,
                    "item_type": r.get("item_type", "material"),
                    "material_id": _parse_emp_id(r.get("material_id")),
                    "service_name": r.get("service_name") or "",
                    "unit_id": _parse_emp_id(r.get("unit_id")),
                    "price": r["price"],
                },
            )
            n += 1
        return n

    def _load_offers(self, company, rows) -> int:
        n = 0
        for r in rows:
            opp = Opportunity.objects.get(
                company=company, code=r["opportunity_id"],
            )
            CommercialOffer.objects.update_or_create(
                company=company, code=r["offer_id"],
                defaults={
                    "opportunity": opp,
                    "offer_date": r.get("offer_date"),
                    "status": r.get("status_id", "draft"),
                    "total_amount": r.get("total_amount"),
                },
            )
            n += 1
        return n

    def _load_offer_lines(self, company, rows) -> int:
        n = 0
        for r in rows:
            offer = CommercialOffer.objects.get(
                company=company, code=r["offer_id"],
            )
            pli = PriceListItem.objects.filter(
                company=company, code=r.get("price_list_item_id"),
            ).first() if r.get("price_list_item_id") else None

            CommercialOfferLine.objects.update_or_create(
                company=company,
                offer=offer,
                description=r["description"],
                defaults={
                    "price_list_item": pli,
                    "quantity": r["quantity"],
                    "unit_price": r["unit_price"],
                    "line_amount": r.get("line_amount"),
                },
            )
            n += 1
        return n

    def _load_contracts(self, company, rows) -> int:
        n = 0
        for r in rows:
            Contract.objects.update_or_create(
                company=company, code=r["contract_id"],
                defaults={
                    "counterparty_id": self._resolve_cp(r.get("counterparty_id"), company),
                    "contract_number": r.get("contract_number", ""),
                    "contract_date": r.get("contract_date"),
                    "contract_amount": r.get("contract_amount"),
                    "status": r.get("status_id", "draft"),
                    "covered_objects_json": r.get("covered_objects_json", []),
                },
            )
            n += 1
        return n

    # ----------------------------------------------------------
    # Утилиты
    # ----------------------------------------------------------

    def _resolve_cp(self, code: str | None, company) -> int | None:
        """'CP-005' → Counterparty.id (или None)."""
        if not code:
            return None
        cp = Counterparty.objects.filter(company=company, code=code).first()
        return cp.id if cp else None

    def _emit_events(self, company) -> None:
        """Публикует события на каждого лида, сделку и КП — для проверки workflow."""
        for lead in Lead.objects.filter(company=company):
            EventBus.publish(
                CRM.LEAD_CREATE,
                company_id=company.id,
                payload={
                    "lead_id": lead.id,
                    "code": lead.code,
                    "lead_status_id": lead.lead_status_id,
                    "responsible_employee_id": lead.responsible_employee_id,
                },
            )
        for opp in Opportunity.objects.filter(company=company):
            EventBus.publish(
                CRM.OPPORTUNITY_CREATE,
                company_id=company.id,
                payload={
                    "opportunity_id": opp.id,
                    "code": opp.code,
                    "lead_id": opp.lead_id,
                    "amount": float(opp.amount) if opp.amount else None,
                },
            )


def _parse_emp_id(value) -> int | None:
    """'EMP-010' → 10; 'NP-001' → 1; 'MAT-006' → 6; None → None."""
    if not value:
        return None
    try:
        if isinstance(value, int):
            return value
        s = str(value)
        for prefix in ("EMP-", "NP-", "MAT-", "UNIT-", "DOC-"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("0")
        return int(s) if s else None
    except (ValueError, TypeError):
        return None