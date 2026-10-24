-- =====================================================================================
-- Procurement — запросы для отчётов
-- =====================================================================================

-- Q-PROC-R01: Заявка на закупку
SELECT 
    rl.material_id,
    rl.quantity,
    rl.estimated_unit_cost,
    rl.quantity * rl.estimated_unit_cost AS total_estimated_cost
FROM procurement_requisition_line rl
WHERE rl.requisition_id = :requisition_id;

-- Итог
SELECT SUM(quantity * estimated_unit_cost) AS total_estimated_cost
FROM procurement_requisition_line
WHERE requisition_id = :requisition_id;

-- Q-PROC-R02: Сравнительная ведомость предложений
SELECT 
    s.supplier_id,
    q.material_id,
    q.unit_price,
    q.quantity,
    q.delivery_days,
    q.unit_price * q.quantity AS total_price
FROM procurement_supplier_quote q
JOIN procurement_rfq_supplier rs ON rs.rfq_supplier_id = q.rfq_supplier_id
JOIN procurement_supplier s ON s.supplier_id = rs.supplier_id
WHERE rs.rfq_id = :rfq_id
ORDER BY q.unit_price;

-- Q-PROC-R03: Заказ поставщику
SELECT 
    ol.material_id,
    ol.quantity,
    ol.unit_price,
    ol.total_price,
    ol.received_quantity
FROM procurement_order_line ol
WHERE ol.order_id = :order_id;

-- Итог
SELECT SUM(total_price) AS total_amount
FROM procurement_order_line
WHERE order_id = :order_id;

-- Q-PROC-R04: Анализ выполнения заказов поставщиками
SELECT 
    s.supplier_id,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_amount,
    ROUND(100.0 * COUNT(*) FILTER (WHERE o.actual_delivery_date <= o.expected_delivery_date) / NULLIF(COUNT(o.order_id), 0), 1) AS on_time_percent,
    ROUND(AVG(
        CASE 
            WHEN o.actual_delivery_date > o.expected_delivery_date 
            THEN EXTRACT(DAY FROM (o.actual_delivery_date - o.expected_delivery_date))
            ELSE 0
        END
    ), 1) AS avg_delay_days
FROM procurement_supplier s
JOIN procurement_order o ON o.supplier_id = s.supplier_id
WHERE o.status_id = 'completed'
  AND o.order_date >= :period_from
  AND o.order_date <= :period_to
GROUP BY s.supplier_id
ORDER BY on_time_percent DESC;