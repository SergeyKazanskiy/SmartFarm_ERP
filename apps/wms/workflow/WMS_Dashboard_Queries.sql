-- =====================================================================================
-- WMS — запросы для дашбордов (см. WMS_Dashboards_Roles.yml)
-- Диалект: PostgreSQL. Использует WMS_Schema.json версии 1.2.
-- Параметры :period_from / :period_to — период отчёта, передаются из UI дашборда.
-- =====================================================================================


-- =====================================================================================
-- DASH-WMS-01. Остатки и дефицит
-- =====================================================================================

-- Q-WMS-01-01 (W01-01, Indicator): Позиции с остатком ниже точки перезаказа
WITH stock AS (
    SELECT material_id, SUM(quantity) AS total_quantity
    FROM wms_inventory
    GROUP BY material_id
)
SELECT COUNT(*) AS deficit_items
FROM wms_material m
LEFT JOIN stock s ON s.material_id = m.material_id
WHERE m.min_stock_level IS NOT NULL
  AND COALESCE(s.total_quantity, 0) < m.min_stock_level;

-- Q-WMS-01-02 (W01-02, Indicator): Общая стоимость остатков склада
SELECT SUM(quantity * unit_cost) AS total_inventory_value
FROM wms_inventory
WHERE unit_cost IS NOT NULL;

-- Q-WMS-01-03 (W01-03, Table): Ведомость дефицита
WITH stock AS (
    SELECT material_id, SUM(quantity) AS total_quantity
    FROM wms_inventory
    GROUP BY material_id
)
SELECT m.material_id,
       m.material_name,
       m.min_stock_level,
       COALESCE(s.total_quantity, 0) AS current_quantity,
       m.min_stock_level - COALESCE(s.total_quantity, 0) AS shortage_quantity
FROM wms_material m
LEFT JOIN stock s ON s.material_id = m.material_id
WHERE m.min_stock_level IS NOT NULL
  AND COALESCE(s.total_quantity, 0) < m.min_stock_level
ORDER BY shortage_quantity DESC;

-- Q-WMS-01-04 (W01-04, PieChart): Структура остатков по группам материалов
SELECT mg.material_group_name,
       SUM(i.quantity * i.unit_cost) AS group_value
FROM wms_inventory i
JOIN wms_material m ON m.material_id = i.material_id
LEFT JOIN wms_material_group mg ON mg.material_group_id = m.material_group_id
WHERE i.unit_cost IS NOT NULL
GROUP BY mg.material_group_name
ORDER BY group_value DESC;

-- Q-WMS-01-05 (W01-05, Table): Партии с истекающим сроком годности
SELECT l.lot_id,
       m.material_name,
       l.lot_number,
       l.expiration_date,
       COALESCE(SUM(i.quantity), 0) AS remaining_quantity
FROM wms_material_lot l
JOIN wms_material m ON m.material_id = l.material_id
LEFT JOIN wms_inventory i ON i.lot_id = l.lot_id
WHERE l.expiration_date IS NOT NULL
  AND l.expiration_date <= CURRENT_DATE + INTERVAL '30 days'
GROUP BY l.lot_id, m.material_name, l.lot_number, l.expiration_date
HAVING COALESCE(SUM(i.quantity), 0) > 0
ORDER BY l.expiration_date;


-- =====================================================================================
-- DASH-WMS-02. Приход и обеспечение
-- =====================================================================================

-- Q-WMS-02-01 (W02-01, Indicator): Непроведённые приходные документы
SELECT COUNT(*) AS unposted_receipts
FROM wms_goods_receipt
WHERE status = 'draft';

-- Q-WMS-02-02 (W02-02, LineChart): Динамика поступлений по месяцам (в деньгах)
SELECT date_trunc('month', gr.receipt_date) AS month,
       SUM(grl.quantity * grl.unit_cost) AS total_amount
FROM wms_goods_receipt gr
JOIN wms_goods_receipt_line grl ON grl.receipt_id = gr.receipt_id
WHERE gr.status = 'posted'
  AND gr.receipt_date >= :period_from
  AND gr.receipt_date <  :period_to
GROUP BY 1
ORDER BY 1;

-- Q-WMS-02-03 (W02-03, BarChart): ТОП поставщиков по объёму поставок
SELECT gr.counterparty_id,
       SUM(grl.quantity * grl.unit_cost) AS total_amount
FROM wms_goods_receipt gr
JOIN wms_goods_receipt_line grl ON grl.receipt_id = gr.receipt_id
WHERE gr.status = 'posted'
  AND gr.receipt_date >= :period_from
  AND gr.receipt_date <  :period_to
GROUP BY gr.counterparty_id
ORDER BY total_amount DESC
LIMIT 10;


-- =====================================================================================
-- DASH-WMS-03. Движение материалов
-- =====================================================================================

-- Q-WMS-03-01 (W03-01, Indicator): Активные резервирования
SELECT COUNT(*) AS active_reservations
FROM wms_material_reservation
WHERE status = 'reserved';

-- Q-WMS-03-02 (W03-02, PieChart): Распределение движений по типам за период
SELECT transaction_type, COUNT(*) AS transaction_count
FROM wms_inventory_transaction
WHERE transaction_date >= :period_from
  AND transaction_date <  :period_to
GROUP BY transaction_type
ORDER BY transaction_count DESC;

-- Q-WMS-03-03 (W03-03, Table): Непроведённые документы (приход/перемещение/списание)
SELECT 'receipt' AS document_kind, receipt_id AS document_id, receipt_date AS document_date
FROM wms_goods_receipt WHERE status = 'draft'
UNION ALL
SELECT 'transfer', transfer_id, transfer_date
FROM wms_transfer WHERE status = 'draft'
UNION ALL
SELECT 'writeoff', writeoff_id, writeoff_date
FROM wms_writeoff WHERE status = 'draft'
ORDER BY document_date;

-- Q-WMS-03-04 (W03-04, BarChart): ТОП материалов по объёму списания за период
SELECT wl.material_id,
       SUM(wl.quantity) AS total_written_off
FROM wms_writeoff w
JOIN wms_writeoff_line wl ON wl.writeoff_id = w.writeoff_id
WHERE w.status = 'posted'
  AND w.writeoff_date >= :period_from
  AND w.writeoff_date <  :period_to
GROUP BY wl.material_id
ORDER BY total_written_off DESC
LIMIT 10;


-- =====================================================================================
-- DASH-WMS-04. Оборачиваемость запасов (инвестиционная)
-- =====================================================================================

-- Q-WMS-04-01 (W04-01, Indicator): Средняя оборачиваемость (дней)
-- Формула: (Средний остаток за период / Себестоимость проданных товаров за период) * Дней в периоде
WITH avg_stock AS (
    SELECT 
        material_id,
        AVG(quantity * unit_cost) AS avg_value
    FROM wms_inventory
    GROUP BY material_id
),
cogs AS (
    SELECT 
        material_id,
        SUM(quantity * unit_cost) AS total_cogs
    FROM wms_inventory_transaction t
    JOIN wms_inventory i ON i.inventory_id = t.inventory_id
    WHERE t.transaction_type IN ('issue', 'writeoff')
      AND t.transaction_date >= :period_from
      AND t.transaction_date <= :period_to
    GROUP BY material_id
)
SELECT 
    ROUND(
        AVG(COALESCE(a.avg_value, 0)) / NULLIF(SUM(COALESCE(c.total_cogs, 0)), 0) * 
        EXTRACT(DAY FROM (:period_to - :period_from)),
        2
    ) AS avg_turnover_days
FROM avg_stock a
LEFT JOIN cogs c ON c.material_id = a.material_id;

-- Q-WMS-04-02 (W04-02, BarChart): Оборачиваемость по группам материалов
WITH material_turnover AS (
    SELECT 
        m.material_group_id,
        AVG(i.quantity * i.unit_cost) AS avg_value,
        SUM(t.quantity * i.unit_cost) AS cogs
    FROM wms_inventory i
    JOIN wms_material m ON m.material_id = i.material_id
    LEFT JOIN wms_inventory_transaction t ON t.inventory_id = i.inventory_id
        AND t.transaction_type IN ('issue', 'writeoff')
        AND t.transaction_date >= :period_from
        AND t.transaction_date <= :period_to
    GROUP BY m.material_group_id
)
SELECT 
    mg.material_group_name,
    ROUND(
        AVG(avg_value) / NULLIF(SUM(cogs), 0) * 
        EXTRACT(DAY FROM (:period_to - :period_from)),
        2
    ) AS turnover_days
FROM material_turnover mt
JOIN wms_material_group mg ON mg.material_group_id = mt.material_group_id
GROUP BY mg.material_group_name
ORDER BY turnover_days;

-- Q-WMS-04-03 (W04-03, Table): ТОП-10 материалов с самой низкой оборачиваемостью
WITH stock_value AS (
    SELECT 
        material_id,
        SUM(quantity * unit_cost) AS total_value
    FROM wms_inventory
    GROUP BY material_id
),
usage_value AS (
    SELECT 
        i.material_id,
        SUM(t.quantity * i.unit_cost) AS total_used
    FROM wms_inventory_transaction t
    JOIN wms_inventory i ON i.inventory_id = t.inventory_id
    WHERE t.transaction_type IN ('issue', 'writeoff')
      AND t.transaction_date >= :period_from
      AND t.transaction_date <= :period_to
    GROUP BY i.material_id
)
SELECT 
    m.material_name,
    ROUND(COALESCE(s.total_value, 0), 2) AS stock_value,
    ROUND(COALESCE(u.total_used, 0), 2) AS usage_value,
    ROUND(
        COALESCE(s.total_value, 0) / NULLIF(COALESCE(u.total_used, 0), 0) * 
        EXTRACT(DAY FROM (:period_to - :period_from)),
        2
    ) AS turnover_days
FROM wms_material m
LEFT JOIN stock_value s ON s.material_id = m.material_id
LEFT JOIN usage_value u ON u.material_id = m.material_id
WHERE COALESCE(s.total_value, 0) > 0
ORDER BY turnover_days DESC
LIMIT 10;

-- Q-WMS-04-04 (W04-04, LineChart): Динамика стоимости запасов (деньги в товаре)
SELECT 
    date_trunc('month', t.transaction_date) AS month,
    SUM(CASE 
        WHEN t.transaction_type = 'receipt' THEN t.quantity * i.unit_cost
        WHEN t.transaction_type IN ('issue', 'writeoff', 'transfer_out') THEN -(t.quantity * i.unit_cost)
        WHEN t.transaction_type = 'transfer_in' THEN t.quantity * i.unit_cost
        ELSE 0
    END) AS monthly_change
FROM wms_inventory_transaction t
JOIN wms_inventory i ON i.inventory_id = t.inventory_id
WHERE t.transaction_date >= :period_from
  AND t.transaction_date <= :period_to
GROUP BY date_trunc('month', t.transaction_date)
ORDER BY month;



-- =====================================================================================
-- ВСПОМОГАТЕЛЬНЫЙ ЗАПРОС: Расход материалов по заказам Production
-- Используется в отчетах Production (REP-PROD-05)
-- =====================================================================================

-- Q-WMS-HELPER-01: Фактический расход материалов по производственному заказу
-- Параметры: :production_order_id
SELECT 
    m.material_id,
    m.material_name,
    SUM(wo.actual_materials_json->>'quantity') AS total_used
FROM prod_work_order wo
JOIN wms_material m ON m.material_id = (wo.actual_materials_json->>'material_id')
WHERE wo.production_order_id = :production_order_id
GROUP BY m.material_id, m.material_name;