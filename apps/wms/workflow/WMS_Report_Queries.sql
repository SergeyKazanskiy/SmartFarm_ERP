-- =====================================================================================
-- WMS — запросы для отчётов (см. WMS_Reports_Roles.yml)
-- Диалект: PostgreSQL. Использует WMS_Schema.json версии 1.2.
-- Параметры — именованные (:param), совместимы с SQLAlchemy text() в FastAPI.
-- =====================================================================================


-- =====================================================================================
-- REP-WMS-01. Приходный ордер
-- Параметр: :receipt_id
-- =====================================================================================

-- Q-WMS-R01 (шапка)
SELECT warehouse_id, counterparty_id, receipt_date, document_id, status
FROM wms_goods_receipt
WHERE receipt_id = :receipt_id;

-- Q-WMS-R01 (позиции)
SELECT material_id, lot_id, location_id, quantity, unit_cost
FROM wms_goods_receipt_line
WHERE receipt_id = :receipt_id;

-- Q-WMS-R01 (итог)
SELECT SUM(quantity * unit_cost) AS total_amount
FROM wms_goods_receipt_line
WHERE receipt_id = :receipt_id;


-- =====================================================================================
-- REP-WMS-02. Ведомость резервирований
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-WMS-R02
SELECT reservation_id, material_id, task_object_type, task_object_id, quantity, status, reserved_at
FROM wms_material_reservation
WHERE reserved_at >= :period_from
  AND reserved_at <  :period_to
ORDER BY reserved_at;


-- =====================================================================================
-- REP-WMS-03. Накладная на перемещение
-- Параметр: :transfer_id
-- =====================================================================================

-- Q-WMS-R03 (шапка)
SELECT from_warehouse_id, to_warehouse_id, transfer_date, status
FROM wms_transfer
WHERE transfer_id = :transfer_id;

-- Q-WMS-R03 (позиции)
SELECT material_id, quantity
FROM wms_transfer_line
WHERE transfer_id = :transfer_id;


-- =====================================================================================
-- REP-WMS-04. Акт на списание
-- Параметр: :writeoff_id
-- =====================================================================================

-- Q-WMS-R04 (шапка)
SELECT warehouse_id, writeoff_date, reason, status
FROM wms_writeoff
WHERE writeoff_id = :writeoff_id;

-- Q-WMS-R04 (позиции)
SELECT material_id, quantity
FROM wms_writeoff_line
WHERE writeoff_id = :writeoff_id;


-- =====================================================================================
-- REP-WMS-05. Номенклатурный справочник материалов
-- Параметр: :material_group_id (необязательный фильтр — NULL означает "все группы")
-- =====================================================================================

-- Q-WMS-R05
SELECT m.material_code,
       m.material_name,
       m.unit_id,
       m.min_stock_level,
       COALESCE(SUM(i.quantity), 0) AS current_quantity,
       COALESCE(SUM(i.quantity * i.unit_cost), 0) AS current_value
FROM wms_material m
LEFT JOIN wms_inventory i ON i.material_id = m.material_id
WHERE :material_group_id IS NULL OR m.material_group_id = :material_group_id
GROUP BY m.material_id, m.material_code, m.material_name, m.unit_id, m.min_stock_level
ORDER BY m.material_code;


-- =====================================================================================
-- REP-WMS-06. Инвентаризационная ведомость
-- Параметр: :snapshot_id
-- =====================================================================================

-- Q-WMS-R06
SELECT si.snapshot_item_id,
       m.material_name,
       i.location_id,
       si.quantity AS system_quantity,
       si.counted_quantity,
       COALESCE(si.counted_quantity, 0) - si.quantity AS variance_quantity
FROM wms_inventory_snapshot_item si
JOIN wms_inventory i ON i.inventory_id = si.inventory_id
JOIN wms_material m ON m.material_id = i.material_id
WHERE si.snapshot_id = :snapshot_id
ORDER BY m.material_name;


-- =====================================================================================
-- REP-WMS-07. Реестр партий с истекающим сроком годности
-- Параметр: :days_threshold (горизонт в днях, например 30)
-- =====================================================================================

-- Q-WMS-R07
SELECT l.material_id,
       l.lot_number,
       l.expiration_date,
       COALESCE(SUM(i.quantity), 0) AS remaining_quantity
FROM wms_material_lot l
LEFT JOIN wms_inventory i ON i.lot_id = l.lot_id
WHERE l.expiration_date IS NOT NULL
  AND l.expiration_date <= CURRENT_DATE + (:days_threshold || ' days')::interval
GROUP BY l.material_id, l.lot_number, l.expiration_date
HAVING COALESCE(SUM(i.quantity), 0) > 0
ORDER BY l.expiration_date;


-- =====================================================================================
-- REP-WMS-08. Стоимость запасов в разрезе складов и групп
-- Параметр: :warehouse_id (NULL — все склады)
-- =====================================================================================

-- Q-WMS-R08
WITH warehouse_stock AS (
    SELECT 
        w.warehouse_name,
        mg.material_group_name,
        SUM(i.quantity) AS total_quantity,
        SUM(i.quantity * i.unit_cost) AS total_value
    FROM wms_inventory i
    JOIN wms_storage_location l ON l.location_id = i.location_id
    JOIN wms_warehouse w ON w.warehouse_id = l.warehouse_id
    JOIN wms_material m ON m.material_id = i.material_id
    LEFT JOIN wms_material_group mg ON mg.material_group_id = m.material_group_id
    WHERE (:warehouse_id IS NULL OR w.warehouse_id = :warehouse_id)
      AND i.unit_cost IS NOT NULL
    GROUP BY w.warehouse_name, mg.material_group_name
),
total AS (
    SELECT SUM(total_value) AS grand_total FROM warehouse_stock
)
SELECT 
    ws.warehouse_name,
    ws.material_group_name,
    ROUND(ws.total_quantity, 2) AS total_quantity,
    ROUND(ws.total_value, 2) AS total_value,
    ROUND(ws.total_value / NULLIF(t.grand_total, 0) * 100, 2) AS percent_of_total
FROM warehouse_stock ws
CROSS JOIN total t
ORDER BY ws.warehouse_name, ws.total_value DESC;