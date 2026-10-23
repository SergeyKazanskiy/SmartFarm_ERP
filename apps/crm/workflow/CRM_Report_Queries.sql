-- =====================================================================================
-- CRM — запросы для отчётов (см. CRM_Reports_Roles.yml)
-- Диалект: PostgreSQL. Использует CRM_Schema.json версии 1.2.
-- Параметры — именованные (:param), совместимы с SQLAlchemy text() в FastAPI.
-- =====================================================================================


-- =====================================================================================
-- REP-CRM-01. Реестр лидов
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-CRM-R01
SELECT l.lead_id,
       ls.lead_source_name,
       st.lead_status_name,
       l.responsible_employee_id,
       l.counterparty_id,
       l.created_at
FROM crm_lead l
LEFT JOIN crm_lead_source ls ON ls.lead_source_id = l.lead_source_id
LEFT JOIN crm_lead_status st ON st.lead_status_id = l.lead_status_id
WHERE l.created_at >= :period_from
  AND l.created_at <  :period_to
ORDER BY l.created_at DESC;


-- =====================================================================================
-- REP-CRM-02. Реестр сделок
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-CRM-R02
SELECT o.opportunity_id,
       os.opportunity_stage_name,
       o.amount,
       o.expected_close_date,
       o.responsible_employee_id,
       o.is_won
FROM crm_opportunity o
LEFT JOIN crm_opportunity_stage os ON os.opportunity_stage_id = o.opportunity_stage_id
WHERE o.expected_close_date >= :period_from
  AND o.expected_close_date <  :period_to
ORDER BY o.expected_close_date;


-- =====================================================================================
-- REP-CRM-03. Журнал активностей
-- Параметры: :employee_id (необязательный фильтр), :period_from, :period_to
-- =====================================================================================

-- Q-CRM-R03
SELECT a.activity_type_id,
       a.lead_id,
       a.opportunity_id,
       a.activity_date,
       a.is_completed,
       a.result
FROM crm_activity a
WHERE (:employee_id IS NULL OR a.employee_id = :employee_id)
  AND a.activity_date >= :period_from
  AND a.activity_date <  :period_to
ORDER BY a.activity_date DESC;


-- =====================================================================================
-- REP-CRM-04. Коммерческое предложение
-- Параметр: :offer_id
-- =====================================================================================

-- Q-CRM-R04 (шапка)
SELECT opportunity_id, offer_date, status_id, total_amount
FROM crm_commercial_offer
WHERE offer_id = :offer_id;

-- Q-CRM-R04 (позиции)
SELECT description, quantity, unit_price, line_amount
FROM crm_commercial_offer_line
WHERE offer_id = :offer_id
ORDER BY offer_line_id;


-- =====================================================================================
-- REP-CRM-05. Прайс-лист
-- Параметр: :price_list_id
-- =====================================================================================

-- Q-CRM-R05
SELECT item_type, material_id, service_name, unit_id, price
FROM crm_price_list_item
WHERE price_list_id = :price_list_id
ORDER BY item_type, material_id;


-- =====================================================================================
-- REP-CRM-06. Реестр договоров
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-CRM-R06
SELECT contract_id,
       counterparty_id,
       contract_number,
       contract_date,
       contract_amount,
       status_id
FROM crm_contract
WHERE contract_date >= :period_from
  AND contract_date <  :period_to
ORDER BY contract_date DESC;


-- =====================================================================================
-- REP-CRM-07. Анализ эффективности продаж по менеджерам
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-CRM-R07
WITH manager_metrics AS (
    SELECT 
        e.employee_id,
        e.personnel_number,
        COUNT(DISTINCT l.lead_id) AS leads_count,
        COUNT(DISTINCT o.opportunity_id) AS opportunities_count,
        COUNT(DISTINCT o.opportunity_id) FILTER (WHERE o.is_won = 1) AS won_count,
        SUM(o.amount) FILTER (WHERE o.is_won = 1) AS total_revenue,
        AVG(EXTRACT(DAY FROM (COALESCE(o.expected_close_date, now()) - o.created_at))) FILTER (WHERE o.is_won = 1) AS avg_cycle_days
    FROM hr_employee e
    LEFT JOIN crm_lead l ON l.responsible_employee_id = e.employee_id
        AND l.created_at >= :period_from AND l.created_at <= :period_to
    LEFT JOIN crm_opportunity o ON o.responsible_employee_id = e.employee_id
        AND o.expected_close_date >= :period_from AND o.expected_close_date <= :period_to
    GROUP BY e.employee_id, e.personnel_number
)
SELECT 
    employee_id,
    personnel_number,
    leads_count,
    opportunities_count,
    won_count,
    ROUND(COALESCE(total_revenue, 0), 2) AS total_revenue,
    ROUND(COALESCE(avg_cycle_days, 0), 1) AS avg_cycle_days,
    ROUND(100.0 * won_count / NULLIF(opportunities_count, 0), 1) AS win_rate
FROM manager_metrics
WHERE opportunities_count > 0 OR leads_count > 0
ORDER BY total_revenue DESC;