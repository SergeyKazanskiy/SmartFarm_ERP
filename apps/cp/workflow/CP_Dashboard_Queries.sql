-- =====================================================================================
-- CP — запросы для дашбордов
-- =====================================================================================

-- =====================================================================================
-- DASH-CP-01. Реестр контрагентов
-- =====================================================================================

-- Q-CP-01-01 (W01-01, Indicator): Всего контрагентов
SELECT COUNT(*) AS total_counterparties
FROM cp_counterparty;

-- Q-CP-01-02 (W01-02, Indicator): Активные контрагенты
SELECT COUNT(*) AS active_counterparties
FROM cp_counterparty
WHERE status_id = 'active';

-- Q-CP-01-03 (W01-03, PieChart): Распределение по типам
SELECT ct.counterparty_type_name,
       COUNT(c.counterparty_id) AS count
FROM cp_counterparty c
JOIN cp_counterparty_type ct ON ct.counterparty_type_id = c.counterparty_type_id
GROUP BY ct.counterparty_type_name
ORDER BY count DESC;

-- Q-CP-01-04 (W01-04, PieChart): Распределение по категориям
SELECT cat.category_name,
       COUNT(c.counterparty_id) AS count
FROM cp_counterparty c
LEFT JOIN cp_category cat ON cat.category_id = c.category_id
GROUP BY cat.category_name
ORDER BY count DESC;

-- Q-CP-01-05 (W01-05, Table): Последние добавленные контрагенты
SELECT counterparty_id,
       code,
       name,
       counterparty_type_id,
       status_id,
       created_at
FROM cp_counterparty
ORDER BY created_at DESC
LIMIT 20;


-- =====================================================================================
-- DASH-CP-02. Аналитика по контрагентам
-- =====================================================================================

-- Q-CP-02-01 (W02-01, Indicator): Средний рейтинг контрагентов
SELECT ROUND(AVG(rating_value), 1) AS avg_rating
FROM cp_rating
WHERE rating_date >= CURRENT_DATE - INTERVAL '1 year';

-- Q-CP-02-02 (W02-02, Table): ТОП-10 контрагентов по рейтингу
SELECT c.code,
       c.name,
       r.rating_value,
       r.rating_type,
       r.rating_date
FROM cp_rating r
JOIN cp_counterparty c ON c.counterparty_id = r.counterparty_id
WHERE r.rating_date = (
    SELECT MAX(rating_date)
    FROM cp_rating r2
    WHERE r2.counterparty_id = r.counterparty_id
)
ORDER BY r.rating_value DESC
LIMIT 10;

-- Q-CP-02-03 (W02-03, BarChart): Количество взаимодействий по типам
SELECT interaction_type,
       COUNT(*) AS count
FROM cp_interaction
WHERE interaction_date >= DATE_TRUNC('month', CURRENT_DATE)
GROUP BY interaction_type
ORDER BY count DESC;


-- =====================================================================================
-- DASH-CP-03. Договоры
-- =====================================================================================

-- Q-CP-03-01 (W03-01, Indicator): Активные договоры
SELECT COUNT(*) AS active_contracts
FROM cp_contract
WHERE status_id = 'active';

-- Q-CP-03-02 (W03-02, Table): Истекающие договоры (30 дней)
SELECT c.contract_number,
       cp.name AS counterparty_name,
       c.valid_to,
       c.contract_type,
       c.amount,
       c.currency_id
FROM cp_contract c
JOIN cp_counterparty cp ON cp.counterparty_id = c.counterparty_id
WHERE c.status_id = 'active'
  AND c.valid_to BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
ORDER BY c.valid_to;

-- Q-CP-03-03 (W03-03, Table): Все договоры по контрагентам
SELECT cp.name AS counterparty_name,
       c.contract_number,
       c.contract_date,
       c.valid_from,
       c.valid_to,
       c.contract_type,
       c.amount,
       c.status_id
FROM cp_contract c
JOIN cp_counterparty cp ON cp.counterparty_id = c.counterparty_id
ORDER BY cp.name, c.contract_date DESC;


-- =====================================================================================
-- DASH-CP-04. Черный список
-- =====================================================================================

-- Q-CP-04-01 (W04-01, Indicator): Контрагентов в черном списке
SELECT COUNT(*) AS blacklisted_count
FROM cp_counterparty
WHERE is_blacklisted = true;

-- Q-CP-04-02 (W04-02, Table): Черный список
SELECT c.code,
       c.name,
       b.block_date,
       b.reason,
       b.blocked_by_employee_id
FROM cp_blacklist b
JOIN cp_counterparty c ON c.counterparty_id = b.counterparty_id
WHERE b.unblock_date IS NULL
ORDER BY b.block_date DESC;