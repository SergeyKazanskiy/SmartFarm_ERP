-- =====================================================================================
-- Finance — запросы для дашбордов (см. Finance_Dashboards_Roles.yml)
-- Диалект: PostgreSQL. Использует Finance_Schema.json версии 1.2.
-- Параметры :period_from / :period_to — период отчёта, передаются из UI дашборда.
-- =====================================================================================


-- =====================================================================================
-- DASH-FIN-01. Бюджет и исполнение
-- =====================================================================================

-- Q-FIN-01-01 (W01-01, Indicator): Утверждённые бюджеты
SELECT COUNT(*) AS approved_budgets
FROM fin_budget
WHERE status_id = 'approved';

-- Q-FIN-01-02 (W01-02, BarChart): План vs факт по центрам затрат
WITH planned AS (
    SELECT cost_center_id, SUM(planned_amount) AS planned_amount
    FROM fin_budget_item
    GROUP BY cost_center_id
),
actual AS (
    SELECT cost_center_id, SUM(amount) AS actual_amount
    FROM fin_financial_transaction
    WHERE transaction_date >= :period_from
      AND transaction_date <  :period_to
    GROUP BY cost_center_id
)
SELECT cc.cost_center_name,
       COALESCE(p.planned_amount, 0) AS planned_amount,
       COALESCE(a.actual_amount, 0) AS actual_amount
FROM fin_cost_center cc
LEFT JOIN planned p ON p.cost_center_id = cc.cost_center_id
LEFT JOIN actual a ON a.cost_center_id = cc.cost_center_id
ORDER BY actual_amount DESC;

-- Q-FIN-01-03 (W01-03, Table): Статьи бюджета с превышением плана
WITH actual AS (
    SELECT cost_center_id, SUM(amount) AS actual_amount
    FROM fin_financial_transaction
    GROUP BY cost_center_id
)
SELECT bi.budget_item_id,
       cc.cost_center_name,
       bi.planned_amount,
       COALESCE(a.actual_amount, 0) AS actual_amount,
       COALESCE(a.actual_amount, 0) - bi.planned_amount AS overrun_amount
FROM fin_budget_item bi
LEFT JOIN fin_cost_center cc ON cc.cost_center_id = bi.cost_center_id
LEFT JOIN actual a ON a.cost_center_id = bi.cost_center_id
WHERE COALESCE(a.actual_amount, 0) > bi.planned_amount
ORDER BY overrun_amount DESC;


-- =====================================================================================
-- DASH-FIN-02. Дебиторская и кредиторская задолженность
-- =====================================================================================

-- Q-FIN-02-01 (W02-01, Indicator): Общая сумма непогашенных счетов к получению (AR)
SELECT SUM(amount) AS total_ar_outstanding
FROM fin_invoice
WHERE invoice_type = 'AR'
  AND status_id IN ('issued', 'partially_paid', 'overdue');

-- Q-FIN-02-02 (W02-02, Indicator): Общая сумма непогашенных счетов к оплате (AP)
SELECT SUM(amount) AS total_ap_outstanding
FROM fin_invoice
WHERE invoice_type = 'AP'
  AND status_id IN ('issued', 'partially_paid', 'overdue');

-- Q-FIN-02-03 (W02-03, Table): Просроченные счета
SELECT invoice_id,
       invoice_type,
       counterparty_id,
       invoice_number,
       due_date,
       amount,
       status_id
FROM fin_invoice
WHERE status_id IN ('issued', 'partially_paid')
  AND due_date < CURRENT_DATE
ORDER BY due_date;

-- Q-FIN-02-04 (W02-04, PieChart): Счета по статусам
SELECT status_id, COUNT(*) AS invoice_count
FROM fin_invoice
GROUP BY status_id
ORDER BY invoice_count DESC;


-- =====================================================================================
-- DASH-FIN-03. Финансовые показатели
-- =====================================================================================

-- Q-FIN-03-01 (W03-01, Table): Финансовые показатели по проектам за период
SELECT fp.financial_project_name,
       fi.indicator_code,
       fi.indicator_value
FROM fin_financial_indicator fi
JOIN fin_financial_project fp ON fp.financial_project_id = fi.financial_project_id
JOIN fin_financial_period per ON per.period_id = fi.period_id
WHERE per.date_from >= :period_from
  AND per.date_to <  :period_to
ORDER BY fp.financial_project_name, fi.indicator_code;

-- Q-FIN-03-02 (W03-02, Indicator): Обороты за период
SELECT SUM(amount) AS total_turnover
FROM fin_financial_transaction
WHERE transaction_date >= :period_from
  AND transaction_date <  :period_to;

-- Q-FIN-03-03 (W03-03, PieChart): Обороты по типам счетов (по дебету проводки)
SELECT a.account_type,
       SUM(t.amount) AS turnover
FROM fin_financial_transaction t
JOIN fin_account a ON a.account_id = t.debit_account_id
WHERE t.transaction_date >= :period_from
  AND t.transaction_date <  :period_to
GROUP BY a.account_type
ORDER BY turnover DESC;


-- =====================================================================================
-- DASH-FIN-04. Денежный поток (Cash Flow)
-- =====================================================================================

-- Q-FIN-04-01 (W04-01, Indicator): Остаток на счетах (денежные средства)
-- Сумма дебетовых остатков по счетам типа 'asset' (касса, банк)
SELECT 
    SUM(COALESCE(ft.amount, 0)) AS cash_balance
FROM fin_account a
LEFT JOIN fin_financial_transaction ft ON ft.debit_account_id = a.account_id
WHERE a.account_type = 'asset'
  AND a.account_code IN ('311', '312', '313', '314')  -- Касса, банковские счета
GROUP BY a.account_id;

-- Q-FIN-04-02 (W04-02, LineChart): Прогноз денежного потока на 3 месяца
-- 1. Ожидаемые поступления (AR)
WITH expected_inflow AS (
    SELECT 
        due_date AS expected_date,
        SUM(amount) AS inflow
    FROM fin_invoice
    WHERE invoice_type = 'AR'
      AND status_id IN ('issued', 'partially_paid')
      AND due_date >= CURRENT_DATE
      AND due_date <= CURRENT_DATE + INTERVAL '3 months'
    GROUP BY due_date
),
-- 2. Ожидаемые выплаты (AP)
expected_outflow AS (
    SELECT 
        due_date AS expected_date,
        SUM(amount) AS outflow
    FROM fin_invoice
    WHERE invoice_type = 'AP'
      AND status_id IN ('issued', 'partially_paid')
      AND due_date >= CURRENT_DATE
      AND due_date <= CURRENT_DATE + INTERVAL '3 months'
    GROUP BY due_date
)
SELECT 
    COALESCE(i.expected_date, o.expected_date) AS expected_date,
    COALESCE(i.inflow, 0) AS expected_inflow,
    COALESCE(o.outflow, 0) AS expected_outflow,
    COALESCE(i.inflow, 0) - COALESCE(o.outflow, 0) AS net_cash_flow
FROM expected_inflow i
FULL OUTER JOIN expected_outflow o ON o.expected_date = i.expected_date
ORDER BY expected_date;

-- Q-FIN-04-03 (W04-03, Table): Крупные ожидаемые поступления и выплаты
SELECT 
    invoice_id,
    invoice_type,
    counterparty_id,
    invoice_number,
    due_date,
    amount,
    status_id
FROM fin_invoice
WHERE status_id IN ('issued', 'partially_paid')
  AND due_date >= CURRENT_DATE
  AND due_date <= CURRENT_DATE + INTERVAL '3 months'
  AND amount > (SELECT AVG(amount) FROM fin_invoice WHERE status_id IN ('issued', 'partially_paid'))
ORDER BY amount DESC
LIMIT 10;