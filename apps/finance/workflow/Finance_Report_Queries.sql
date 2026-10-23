-- =====================================================================================
-- Finance — запросы для отчётов (см. Finance_Reports_Roles.yml)
-- Диалект: PostgreSQL. Использует Finance_Schema.json версии 1.2.
-- Параметры — именованные (:param), совместимы с SQLAlchemy text() в FastAPI.
-- =====================================================================================


-- =====================================================================================
-- REP-FIN-01. Бюджет
-- Параметр: :budget_id
-- =====================================================================================

-- Q-FIN-R01 (позиции)
SELECT cc.cost_center_name,
       bi.planned_amount
FROM fin_budget_item bi
LEFT JOIN fin_cost_center cc ON cc.cost_center_id = bi.cost_center_id
WHERE bi.budget_id = :budget_id
ORDER BY cc.cost_center_name;

-- Q-FIN-R01 (итог)
SELECT SUM(planned_amount) AS total_planned
FROM fin_budget_item
WHERE budget_id = :budget_id;


-- =====================================================================================
-- REP-FIN-02. Реестр счетов
-- Параметры: :period_from, :period_to, :invoice_type (необязательный фильтр AR/AP)
-- =====================================================================================

-- Q-FIN-R02
SELECT invoice_id,
       invoice_type,
       counterparty_id,
       invoice_number,
       invoice_date,
       due_date,
       amount,
       status_id
FROM fin_invoice
WHERE invoice_date >= :period_from
  AND invoice_date <  :period_to
  AND (:invoice_type IS NULL OR invoice_type = :invoice_type)
ORDER BY invoice_date;


-- =====================================================================================
-- REP-FIN-03. Реестр платежей
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-FIN-R03
SELECT payment_id,
       invoice_id,
       payment_date,
       amount,
       payment_status
FROM fin_payment
WHERE payment_date >= :period_from
  AND payment_date <  :period_to
ORDER BY payment_date;


-- =====================================================================================
-- REP-FIN-04. Оборотно-сальдовая ведомость
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-FIN-R04
WITH debit AS (
    SELECT debit_account_id AS account_id, SUM(amount) AS debit_turnover
    FROM fin_financial_transaction
    WHERE transaction_date >= :period_from
      AND transaction_date <  :period_to
    GROUP BY debit_account_id
),
credit AS (
    SELECT credit_account_id AS account_id, SUM(amount) AS credit_turnover
    FROM fin_financial_transaction
    WHERE transaction_date >= :period_from
      AND transaction_date <  :period_to
    GROUP BY credit_account_id
)
SELECT a.account_code,
       a.account_name,
       COALESCE(d.debit_turnover, 0) AS debit_turnover,
       COALESCE(c.credit_turnover, 0) AS credit_turnover
FROM fin_account a
LEFT JOIN debit d ON d.account_id = a.account_id
LEFT JOIN credit c ON c.account_id = a.account_id
WHERE COALESCE(d.debit_turnover, 0) > 0
   OR COALESCE(c.credit_turnover, 0) > 0
ORDER BY a.account_code;


-- =====================================================================================
-- REP-FIN-05. Финансовые показатели по проектам
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-FIN-R05
SELECT fp.financial_project_name,
       fi.indicator_code,
       fi.indicator_value
FROM fin_financial_indicator fi
JOIN fin_financial_project fp ON fp.financial_project_id = fi.financial_project_id
JOIN fin_financial_period per ON per.period_id = fi.period_id
WHERE per.date_from >= :period_from
  AND per.date_to <  :period_to
ORDER BY fp.financial_project_name, fi.indicator_code;


-- =====================================================================================
-- REP-FIN-06. Отчёт о прибылях и убытках (P&L)
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-FIN-R06
WITH turnover AS (
    SELECT 
        a.account_type,
        a.account_code,
        a.account_name,
        SUM(ft.amount) AS debit_turnover
    FROM fin_financial_transaction ft
    JOIN fin_account a ON a.account_id = ft.debit_account_id
    WHERE ft.transaction_date >= :period_from
      AND ft.transaction_date <= :period_to
    GROUP BY a.account_type, a.account_code, a.account_name
    
    UNION ALL
    
    -- Кредитовые обороты (доходы)
    SELECT 
        a.account_type,
        a.account_code,
        a.account_name,
        -SUM(ft.amount) AS debit_turnover  -- Отрицательный знак для кредита
    FROM fin_financial_transaction ft
    JOIN fin_account a ON a.account_id = ft.credit_account_id
    WHERE ft.transaction_date >= :period_from
      AND ft.transaction_date <= :period_to
    GROUP BY a.account_type, a.account_code, a.account_name
)
SELECT 
    account_type,
    account_code,
    account_name,
    SUM(debit_turnover) AS turnover
FROM turnover
WHERE account_type IN ('income', 'expense')
GROUP BY account_type, account_code, account_name
ORDER BY 
    CASE account_type
        WHEN 'income' THEN 1
        WHEN 'expense' THEN 2
    END,
    account_code;

-- Итог по типам счетов (для построения P&L)
SELECT 
    account_type,
    SUM(turnover) AS total_turnover
FROM (
    SELECT 
        account_type,
        SUM(debit_turnover) AS turnover
    FROM turnover
    WHERE account_type IN ('income', 'expense')
    GROUP BY account_type
) sub
GROUP BY account_type
ORDER BY 
    CASE account_type
        WHEN 'income' THEN 1
        WHEN 'expense' THEN 2
    END;