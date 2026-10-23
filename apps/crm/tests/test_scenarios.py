"""
E2E по CRM_Scenarios.yml:
- SCENARIO-CRM-01: Lead → Opportunity
- SCENARIO-CRM-02: Opportunity → Contract
"""
import pytest

from apps.crm.models import (
    ActivityType, CommercialOffer, Contract, Opportunity,
)
from apps.crm.services import (
    ActivityService, CommercialOfferLineService, CommercialOfferService,
    ContractService, LeadService, OpportunityService,
)


@pytest.mark.django_db
def test_scenario_crm_001_lead_to_opportunity(company, lead_status, opp_stage):
    """
    Полный цикл: лид → активность → квалификация → сделка.
    """
    # 1. Создание лида
    lead = LeadService.create(
        company_id=company.id,
        data={"lead_status_id": lead_status.id, "title": "Новый лид"},
        actor_employee_id=10,
    )
    assert lead.lead_status_id == lead_status.id

    # 2. Планирование активности
    at = ActivityType.objects.create(company=company, code="AT-001", name="Звонок")
    act = ActivityService.create(
        company_id=company.id,
        data={"lead_id": lead.id, "activity_type_id": at.id},
        actor_employee_id=10,
    )

    # 3. Завершение активности
    act = ActivityService.complete(
        company_id=company.id, activity_id=act.id,
        result="Потенциал высокий",
    )
    assert act.is_completed

    # 4. Квалификация лида
    lead = LeadService.update_status(
        company_id=company.id, lead_id=lead.id,
        new_status_id=lead_status.id,
    )

    # 5. Создание сделки из лида
    opp = OpportunityService.create(
        company_id=company.id,
        data={
            "lead_id": lead.id,
            "opportunity_stage_id": opp_stage.id,
            "amount": 250000,
            "title": "Сделка из лида",
        },
        actor_employee_id=10,
    )

    assert opp.lead_id == lead.id
    assert opp.amount == 250000


@pytest.mark.django_db
def test_scenario_crm_002_opportunity_to_contract(company, opportunity):
    """
    Полный цикл: КП → отправка → принятие → выигрыш сделки → договор.
    """
    # 1. Создание КП
    offer = CommercialOfferService.create(
        company_id=company.id,
        data={"opportunity_id": opportunity.id},
    )

    # 2. Добавление позиции
    CommercialOfferLineService.create(
        company_id=company.id,
        data={
            "offer_id": offer.id,
            "description": "Телевизор X-100",
            "quantity": 50,
            "unit_price": 5500,
        },
    )

    # 3. Отправка
    offer = CommercialOfferService.send(
        company_id=company.id, offer_id=offer.id,
    )
    assert offer.status == "sent"
    assert float(offer.total_amount) == 275000.0

    # 4. Принятие
    offer = CommercialOfferService.accept(
        company_id=company.id, offer_id=offer.id,
    )
    assert offer.status == "accepted"

    # 5. Выигрыш сделки
    opportunity = OpportunityService.win(
        company_id=company.id, opportunity_id=opportunity.id,
    )
    assert opportunity.is_won == 1

    # 6. Создание договора
    contract = ContractService.create(
        company_id=company.id,
        data={
            "counterparty_id": 1,
            "contract_number": "CONTR-001",
            "contract_date": opportunity.expected_close_date,
            "contract_amount": 275000,
        },
    )

    # 7. Активация
    contract = ContractService.activate(
        company_id=company.id, contract_id=contract.id,
    )
    assert contract.status == "active"