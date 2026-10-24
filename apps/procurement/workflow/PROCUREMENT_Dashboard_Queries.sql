-- =====================================================================================
-- Procurement — запросы для дашбордов
-- =====================================================================================

-- =====================================================================================
-- DASH-PROC-01. Дефицит и заявки
-- =====================================================================================

-- Q-PROC-01-01 (W01-01): Материалы с дефицитом (ниже точки перезаказа)
WITH stock AS (
    SELECT material_id, SUM(quantity) AS total_quantity
    FROM wms_inventory
    GROUP BY material_id
)
SELECT COUNT(*) AS deficit_count
FROM wms_material m
LEFT JOIN stock s ON s.material_id = m.material_id
WHERE m.min_stock_level IS NOT NULL
  AND COALESCE(s.total_quantity, 0) < m.min_stock_level;

-- Q-PROC-01-02 (W01-02): Активные заявки на закупку (ожидают согласования)
SELECT COUNT(*) AS pending_requisitions
FROM procurement_requisition
WHERE status_id = 'pending_approval';

-- Q-PROC-01-03 (W01-03, Table): Дефицитные материалы с потребностью в закупке
WITH stock AS (
    SELECT material_id, SUM(quantity) AS total_quantity
    FROM wms_inventory
    GROUP BY material_id
)
SELECT 
    m.material_id,
    m.material_name,
    m.min_stock_level,
    COALESCE(s.total_quantity, 0) AS current_quantity,
    m.min_stock_level - COALESCE(s.total_quantity, 0) AS shortage_quantity,
    CASE 
        WHEN r.requisition_id IS NOT NULL THEN 'В закупке'
        ELSE 'Требуется заявка'
    END AS status
FROM wms_material m
LEFT JOIN stock s ON s.material_id = m.material_id
LEFT JOIN (
    SELECT DISTINCT rl.material_id, r.requisition_id
    FROM procurement_requisition r
    JOIN procurement_requisition_line rl ON rl.requisition_id = r.requisition_id
    WHERE r.status_id IN ('approved', 'ordered')
) r ON r.material_id = m.material_id
WHERE m.min_stock_level IS NOT NULL
  AND COALESCE(s.total_quantity, 0) < m.min_stock_level
ORDER BY shortage_quantity DESC;

-- Q-PROC-01-04 (W01-04, BarChart): Прогноз потребности в материалах на неделю
-- (Прогноз на основе плана производства из модуля Production)
SELECT 
    m.material_name,
    SUM(po.planned_quantity * bi.quantity) AS predicted_need
FROM prod_production_order po
JOIN prod_bom_item bi ON bi.bom_id = po.bom_id
JOIN wms_material m ON m.material_id = bi.material_id
WHERE po.planned_start_date >= CURRENT_DATE
  AND po.planned_start_date <= CURRENT_DATE + INTERVAL '7 days'
  AND po.status_id IN ('confirmed', 'in_progress')
GROUP BY m.material_id, m.material_name
ORDER BY predicted_need DESC
LIMIT 10;


-- =====================================================================================
-- DASH-PROC-02. Анализ поставщиков
-- =====================================================================================

-- Q-PROC-02-01 (W02-01): Средний рейтинг поставщиков
SELECT ROUND(AVG(rating), 1) AS avg_rating
FROM procurement_supplier
WHERE rating IS NOT NULL;

-- Q-PROC-02-02 (W02-02, PieChart): Распределение заказов по поставщикам
SELECT 
    s.supplier_id,
    s.rating,
    COUNT(o.order_id) AS order_count
FROM procurement_supplier s
JOIN procurement_order o ON o.supplier_id = s.supplier_id
GROUP BY s.supplier_id, s.rating
ORDER BY order_count DESC;

-- Q-PROC-02-03 (W02-03, Table): Поставщики с нарушением сроков
SELECT 
    s.supplier_id,
    s.rating,
    COUNT(o.order_id) AS total_orders,
    COUNT(*) FILTER (WHERE o.actual_delivery_date > o.expected_delivery_date) AS late_deliveries,
    ROUND(100.0 * COUNT(*) FILTER (WHERE o.actual_delivery_date > o.expected_delivery_date) / NULLIF(COUNT(o.order_id), 0), 1) AS late_percent
FROM procurement_supplier s
JOIN procurement_order o ON o.supplier_id = s.supplier_id
WHERE o.status_id = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY s.supplier_id, s.rating
HAVING COUNT(*) FILTER (WHERE o.actual_delivery_date > o.expected_delivery_date) > 0
ORDER BY late_percent DESC;

-- Q-PROC-02-04 (W02-04, BarChart): ТОП поставщиков по объёму закупок
SELECT 
    s.supplier_id,
    SUM(o.total_amount) AS total_spent
FROM procurement_supplier s
JOIN procurement_order o ON o.supplier_id = s.supplier_id
WHERE o.status_id = 'completed'
  AND o.order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY s.supplier_id
ORDER BY total_spent DESC
LIMIT 10;


-- =====================================================================================
-- DASH-PROC-03. Заказы и поставки
-- =====================================================================================

-- Q-PROC-03-01 (W03-01): Заказы со статусом 'sent' (ожидают подтверждения)
SELECT COUNT(*) AS orders_sent
FROM procurement_order
WHERE status_id = 'sent';

-- Q-PROC-03-02 (W03-02): Просроченные поставки
SELECT COUNT(*) AS overdue_deliveries
FROM procurement_order
WHERE status_id IN ('sent', 'confirmed')
  AND expected_delivery_date < CURRENT_DATE;

-- Q-PROC-03-03 (W03-03, LineChart): Динамика закупок по месяцам (в деньгах)
SELECT 
    DATE_TRUNC('month', order_date) AS month,
    SUM(total_amount) AS total_amount
FROM procurement_order
WHERE status_id = 'completed'
  AND order_date >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;

-- Q-PROC-03-04 (W03-04, Table): Незавершённые заказы (поставка ожидается)
SELECT 
    o.order_id,
    o.order_number,
    s.supplier_id,
    o.expected_delivery_date,
    o.status_id,
    o.total_amount,
    (CURRENT_DATE - o.expected_delivery_date) AS days_overdue
FROM procurement_order o
JOIN procurement_supplier s ON s.supplier_id = o.supplier_id
WHERE o.status_id IN ('sent', 'confirmed')
ORDER BY o.expected_delivery_date;

-- Q-PROC-03-05 (W03-05): Общая сумма активных заказов
SELECT COALESCE(SUM(total_amount), 0) AS total_active_orders
FROM procurement_order
WHERE status_id IN ('sent', 'confirmed');