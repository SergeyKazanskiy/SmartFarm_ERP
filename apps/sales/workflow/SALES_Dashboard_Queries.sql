-- =====================================================================================
-- Sales — запросы для дашбордов
-- =====================================================================================

-- =====================================================================================
-- DASH-SALES-01. Воронка продаж
-- =====================================================================================

-- Q-SALES-01-01 (W01-01): Активные возможности
SELECT COUNT(*) AS active_opportunities
FROM sales_opportunity
WHERE stage_id NOT IN ('closed_won', 'closed_lost');

-- Q-SALES-01-02 (W01-02, Funnel): Воронка по стадиям
SELECT 
    stage_id,
    COUNT(*) AS opportunities,
    SUM(expected_value) AS expected_value
FROM sales_opportunity
WHERE stage_id IS NOT NULL
GROUP BY stage_id
ORDER BY 
    CASE stage_id
        WHEN 'lead' THEN 1
        WHEN 'negotiation' THEN 2
        WHEN 'proposal' THEN 3
        WHEN 'closed_won' THEN 4
        WHEN 'closed_lost' THEN 5
    END;

-- Q-SALES-01-03 (W01-03): Ожидаемая сумма сделок (weighted pipeline)
SELECT 
    SUM(expected_value * probability_percent / 100) AS weighted_pipeline
FROM sales_opportunity
WHERE stage_id NOT IN ('closed_won', 'closed_lost');

-- Q-SALES-01-04 (W01-04, Table): Мои активные возможности
SELECT 
    opportunity_id,
    opportunity_name,
    customer_id,
    stage_id,
    expected_value,
    probability_percent,
    expected_close_date
FROM sales_opportunity
WHERE created_by_employee_id = :employee_id
  AND stage_id NOT IN ('closed_won', 'closed_lost')
ORDER BY expected_close_date;

-- Q-SALES-01-05 (W01-05, BarChart): Конверсия менеджеров
SELECT 
    e.employee_id,
    e.personnel_number,
    COUNT(DISTINCT opp.opportunity_id) AS total_opportunities,
    COUNT(DISTINCT o.order_id) AS won_orders,
    ROUND(100.0 * COUNT(DISTINCT o.order_id) / NULLIF(COUNT(DISTINCT opp.opportunity_id), 0), 1) AS conversion_rate
FROM hr_employee e
LEFT JOIN sales_opportunity opp ON opp.created_by_employee_id = e.employee_id
LEFT JOIN sales_order o ON o.customer_id = opp.customer_id AND o.status_id = 'completed'
WHERE e.employee_id = :employee_id OR :employee_id IS NULL
GROUP BY e.employee_id, e.personnel_number
ORDER BY conversion_rate DESC;


-- =====================================================================================
-- DASH-SALES-02. Клиентская база
-- =====================================================================================

-- Q-SALES-02-01 (W02-01): Всего клиентов
SELECT COUNT(*) AS total_customers
FROM sales_customer
WHERE is_active = true;

-- Q-SALES-02-02 (W02-02, PieChart): Распределение клиентов по категориям
SELECT 
    customer_category,
    COUNT(*) AS customer_count
FROM sales_customer
WHERE is_active = true
GROUP BY customer_category
ORDER BY customer_count DESC;


-- =====================================================================================
-- DASH-SALES-03. Заказы и отгрузки
-- =====================================================================================

-- Q-SALES-03-01 (W03-01): Заказы со статусом 'confirmed'
SELECT COUNT(*) AS confirmed_orders
FROM sales_order
WHERE status_id = 'confirmed';

-- Q-SALES-03-02 (W03-02): Заказы в производстве
SELECT COUNT(*) AS in_production_orders
FROM sales_order
WHERE status_id = 'in_production';

-- Q-SALES-03-03 (W03-03): Заказы к отгрузке (готовы)
SELECT COUNT(*) AS ready_to_ship_orders
FROM sales_order
WHERE status_id = 'ready_to_ship';

-- Q-SALES-03-04 (W03-04, Table): Последние заказы
SELECT 
    order_id,
    order_number,
    customer_id,
    total_amount,
    order_date,
    expected_ship_date,
    status_id
FROM sales_order
WHERE status_id IN ('confirmed', 'in_production', 'ready_to_ship')
ORDER BY order_date DESC
LIMIT 20;

-- Q-SALES-03-05 (W03-05, LineChart): Динамика продаж по месяцам
SELECT 
    DATE_TRUNC('month', order_date) AS month,
    SUM(total_amount) AS total_sales
FROM sales_order
WHERE status_id = 'completed'
  AND order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;


-- =====================================================================================
-- DASH-SALES-04. Эффективность продаж (инвестиционный)
-- =====================================================================================

-- Q-SALES-04-01 (W04-01): Средний цикл сделки (дней)
WITH closed_deals AS (
    SELECT 
        opportunity_id,
        created_at,
        updated_at,
        expected_close_date
    FROM sales_opportunity
    WHERE stage_id = 'closed_won'
      AND created_at IS NOT NULL
)
SELECT 
    ROUND(AVG(
        EXTRACT(DAY FROM (COALESCE(expected_close_date, updated_at) - created_at))
    ), 1) AS avg_cycle_days
FROM closed_deals;

-- Q-SALES-04-02 (W04-02): Коэффициент конверсии лидов в заказы
SELECT 
    ROUND(
        100.0 * (
            SELECT COUNT(DISTINCT o.order_id)
            FROM sales_order o
            JOIN sales_opportunity opp ON opp.customer_id = o.customer_id
            WHERE o.status_id = 'completed'
        ) / 
        NULLIF((SELECT COUNT(*) FROM sales_opportunity WHERE stage_id != 'closed_lost'), 0),
        1
    ) AS conversion_rate;

-- Q-SALES-04-03 (W04-03, BarChart): ТОП-5 менеджеров по выручке
SELECT 
    e.employee_id,
    e.personnel_number,
    SUM(o.total_amount) AS total_revenue
FROM hr_employee e
JOIN sales_order o ON o.created_by_employee_id = e.employee_id
WHERE o.status_id = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY e.employee_id, e.personnel_number
ORDER BY total_revenue DESC
LIMIT 5;

-- Q-SALES-04-04 (W04-04, Table): ТОП-10 клиентов по выручке
SELECT 
    c.customer_id,
    c.customer_category,
    SUM(o.total_amount) AS total_revenue,
    COUNT(o.order_id) AS order_count
FROM sales_customer c
JOIN sales_order o ON o.customer_id = c.customer_id
WHERE o.status_id = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY c.customer_id, c.customer_category
ORDER BY total_revenue DESC
LIMIT 10;