-- =====================================================================================
-- Sales — запросы для отчётов
-- =====================================================================================

-- Q-SALES-R01: Отчёт по воронке продаж
SELECT 
    stage_id,
    COUNT(*) AS opportunities_count,
    SUM(expected_value) AS expected_value,
    ROUND(AVG(probability_percent), 1) AS avg_probability
FROM sales_opportunity
WHERE created_at >= :period_from
  AND created_at <= :period_to
GROUP BY stage_id
ORDER BY 
    CASE stage_id
        WHEN 'lead' THEN 1
        WHEN 'negotiation' THEN 2
        WHEN 'proposal' THEN 3
        WHEN 'closed_won' THEN 4
        WHEN 'closed_lost' THEN 5
    END;

-- Q-SALES-R02: Коммерческое предложение
SELECT 
    ql.material_id,
    ql.quantity,
    ql.unit_price,
    ql.discount_percent,
    ql.total_price
FROM sales_quote_line ql
WHERE ql.quote_id = :quote_id;

-- Итог
SELECT SUM(total_price) AS total_amount
FROM sales_quote_line
WHERE quote_id = :quote_id;

-- Q-SALES-R03: Заказ клиента
SELECT 
    ol.material_id,
    ol.quantity,
    ol.unit_price,
    ol.discount_percent,
    ol.total_price,
    ol.shipped_quantity
FROM sales_order_line ol
WHERE ol.order_id = :order_id;

-- Итог
SELECT SUM(total_price) AS total_amount
FROM sales_order_line
WHERE order_id = :order_id;

-- Q-SALES-R04: Отгрузочная ведомость
SELECT 
    sl.material_id,
    sl.quantity,
    sl.order_line_id
FROM sales_shipment_line sl
WHERE sl.shipment_id = :shipment_id;

-- Q-SALES-R05: Счет на оплату
SELECT 
    ol.material_id,
    ol.quantity,
    ol.unit_price,
    ol.discount_percent,
    ol.total_price
FROM sales_order_line ol
WHERE ol.order_id = (SELECT order_id FROM sales_invoice WHERE invoice_id = :invoice_id);

-- Итог
SELECT total_amount
FROM sales_invoice
WHERE invoice_id = :invoice_id;

-- Q-SALES-R06: Анализ продаж по менеджерам
SELECT 
    e.employee_id,
    e.personnel_number,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_revenue,
    ROUND(AVG(o.total_amount), 2) AS avg_order_value
FROM hr_employee e
JOIN sales_order o ON o.created_by_employee_id = e.employee_id
WHERE o.status_id = 'completed'
  AND o.order_date >= :period_from
  AND o.order_date <= :period_to
GROUP BY e.employee_id, e.personnel_number
ORDER BY total_revenue DESC;