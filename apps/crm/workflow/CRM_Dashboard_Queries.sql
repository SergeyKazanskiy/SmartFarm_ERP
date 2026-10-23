-- =====================================================================================
-- CRM — запросы для дашбордов (см. CRM_Dashboards_Roles.yml)
-- Диалект: PostgreSQL. Использует CRM_Schema.json версии 1.2.
-- Параметры :period_from / :period_to — период отчёта, передаются из UI дашборда.
-- =====================================================================================


-- =====================================================================================
-- DASH-CRM-01. Воронка продаж
-- =====================================================================================

-- Q-CRM-01-01 (W01-01, Indicator): Открытые сделки
SELECT COUNT(*) AS open_opportunities
FROM crm_opportunity
WHERE is_won IS NULL;

-- Q-CRM-01-02 (W01-02, Indicator): Сумма открытых сделок (pipeline)
SELECT SUM(amount) AS pipeline_amount
FROM crm_opportunity
WHERE is_won IS NULL;

-- Q-CRM-01-03 (W01-03, PieChart): Распределение сделок по стадиям
SELECT os.opportunity_stage_name,
       COUNT(o.opportunity_id) AS opportunity_count
FROM crm_opportunity o
LEFT JOIN crm_opportunity_stage os ON os.opportunity_stage_id = o.opportunity_stage_id
WHERE o.is_won IS NULL
GROUP BY os.opportunity_stage_name
ORDER BY opportunity_count DESC;

-- Q-CRM-01-04 (W01-04, Indicator): % выигранных сделок (win rate)
SELECT ROUND(
         100.0 * COUNT(*) FILTER (WHERE is_won = 1)
         / NULLIF(COUNT(*) FILTER (WHERE is_won IS NOT NULL), 0),
         1
       ) AS win_rate_percent
FROM crm_opportunity;

-- Q-CRM-01-05 (W01-05, BarChart): Динамика выигранных/проигранных сделок по месяцам
SELECT date_trunc('month', expected_close_date) AS month,
       COUNT(*) FILTER (WHERE is_won = 1) AS won_count,
       COUNT(*) FILTER (WHERE is_won = 0) AS lost_count
FROM crm_opportunity
WHERE is_won IS NOT NULL
  AND expected_close_date >= :period_from
  AND expected_close_date <  :period_to
GROUP BY 1
ORDER BY 1;


-- =====================================================================================
-- DASH-CRM-02. Активность менеджеров
-- =====================================================================================

-- Q-CRM-02-01 (W02-01, Indicator): Активности за период
SELECT COUNT(*) AS activities_count
FROM crm_activity
WHERE activity_date >= :period_from
  AND activity_date <  :period_to;

-- Q-CRM-02-02 (W02-02, Table): Просроченные активности
SELECT activity_id,
       activity_type_id,
       lead_id,
       opportunity_id,
       employee_id,
       activity_date
FROM crm_activity
WHERE is_completed = 0
  AND activity_date < now()
ORDER BY activity_date;

-- Q-CRM-02-03 (W02-03, BarChart): Количество активностей по менеджерам
SELECT employee_id,
       COUNT(*) AS activities_count
FROM crm_activity
WHERE activity_date >= :period_from
  AND activity_date <  :period_to
GROUP BY employee_id
ORDER BY activities_count DESC
LIMIT 20;


-- =====================================================================================
-- DASH-CRM-03. Договоры
-- =====================================================================================

-- Q-CRM-03-01 (W03-01, Indicator): Активные договоры
SELECT COUNT(*) AS active_contracts
FROM crm_contract
WHERE status_id = 'active';

-- Q-CRM-03-02 (W03-02, Indicator): Сумма активных договоров
SELECT SUM(contract_amount) AS active_contracts_amount
FROM crm_contract
WHERE status_id = 'active';

-- Q-CRM-03-03 (W03-03, Table): Договоры, ожидающие активации
SELECT contract_id,
       counterparty_id,
       contract_number,
       contract_date,
       contract_amount
FROM crm_contract
WHERE status_id = 'draft'
ORDER BY contract_date;



-- =====================================================================================
-- DASH-CRM-04. Эффективность продаж (инвестиционная)
-- =====================================================================================

-- Q-CRM-04-01 (W04-01, Indicator): Средний цикл сделки (дней)
WITH closed_deals AS (
    SELECT 
        opportunity_id,
        created_at,
        expected_close_date
    FROM crm_opportunity
    WHERE is_won = 1
      AND created_at IS NOT NULL
)
SELECT 
    ROUND(AVG(
        EXTRACT(DAY FROM (COALESCE(expected_close_date, now()) - created_at))
    ), 1) AS avg_cycle_days
FROM closed_deals;

-- Q-CRM-04-02 (W04-02, Indicator): Средняя сумма выигранной сделки
SELECT 
    ROUND(AVG(amount), 2) AS avg_won_amount
FROM crm_opportunity
WHERE is_won = 1;

-- Q-CRM-04-03 (W04-03, BarChart): ТОП-5 менеджеров по выручке
SELECT 
    e.employee_id,
    e.personnel_number,
    COUNT(o.opportunity_id) AS deals_won,
    SUM(o.amount) AS total_revenue
FROM hr_employee e
JOIN crm_opportunity o ON o.responsible_employee_id = e.employee_id
WHERE o.is_won = 1
  AND o.expected_close_date >= :period_from
  AND o.expected_close_date <= :period_to
GROUP BY e.employee_id, e.personnel_number
ORDER BY total_revenue DESC
LIMIT 5;

-- Q-CRM-04-04 (W04-04, PieChart): Распределение причин проигрыша сделок
SELECT 
    lost_reason,
    COUNT(*) AS lost_count
FROM crm_opportunity
WHERE is_won = 0
  AND lost_reason IS NOT NULL
  AND expected_close_date >= :period_from
  AND expected_close_date <= :period_to
GROUP BY lost_reason
ORDER BY lost_count DESC;

-- Q-CRM-04-05 (W04-05, LineChart): Динамика win rate по месяцам
WITH monthly_stats AS (
    SELECT 
        DATE_TRUNC('month', expected_close_date) AS month,
        COUNT(*) FILTER (WHERE is_won = 1) AS won_count,
        COUNT(*) FILTER (WHERE is_won = 0) AS lost_count
    FROM crm_opportunity
    WHERE is_won IS NOT NULL
      AND expected_close_date >= :period_from
      AND expected_close_date <= :period_to
    GROUP BY DATE_TRUNC('month', expected_close_date)
)
SELECT 
    month,
    won_count,
    lost_count,
    ROUND(100.0 * won_count / NULLIF(won_count + lost_count, 0), 1) AS win_rate
FROM monthly_stats
ORDER BY month;