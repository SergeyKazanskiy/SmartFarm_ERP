-- =====================================================================================
-- Production — запросы для отчётов (см. Production_Reports_Roles.yml)
-- Диалект: PostgreSQL. Коды запросов соответствуют query_ref в YAML-файле ролей.
--
-- Использует Production_Schema.json версии 1.2: status_id есть на
-- prod_production_order/prod_work_order/prod_operation_execution, actual_materials_json
-- есть на prod_work_order, unit_cost есть на prod_bom_item, *_json-поля — нативный
-- jsonb. Никаких ALTER TABLE и примечаний о недостающих полях не требуется.
--
-- Параметры — именованные (:param), совместимы с SQLAlchemy text() в FastAPI.
-- =====================================================================================


-- =====================================================================================
-- REP-PROD-01. Наряд на выполнение работ
-- Параметр: :work_order_id
-- Печатная форма для мастера/бригады: перечень операций наряда по маршруту заказа,
-- с плановыми ресурсами и фактическим статусом выполнения по каждой операции.
-- =====================================================================================

-- Q-PROD-R01
SELECT od.sequence_no,
       od.operation_name,
       wc.work_center_name,
       od.resources_json,
       oe.status_id,
       oe.performed_by_employee_id,
       oe.start_time,
       oe.end_time
FROM prod_work_order wo
JOIN prod_production_order po ON po.production_order_id = wo.production_order_id
JOIN prod_operation_definition od ON od.routing_id = po.routing_id
LEFT JOIN prod_work_center wc ON wc.work_center_id = od.work_center_id
LEFT JOIN prod_operation_execution oe
       ON oe.work_order_id = wo.work_order_id
      AND oe.operation_id = od.operation_id
WHERE wo.work_order_id = :work_order_id
ORDER BY od.sequence_no;


-- =====================================================================================
-- REP-PROD-02. Маршрутный лист заказа
-- Параметр: :production_order_id
-- Полная технологическая карта заказа: последовательность операций, ресурсы,
-- целевые параметры, признак контроля качества — для технолога/мастера/планировщика.
-- =====================================================================================

-- Q-PROD-R02
SELECT od.sequence_no,
       od.operation_name,
       wc.work_center_name,
       od.resources_json,
       od.parameters_json,
       EXISTS (
           SELECT 1 FROM prod_quality_point qp WHERE qp.operation_id = od.operation_id
       ) AS has_quality_control
FROM prod_production_order po
JOIN prod_operation_definition od ON od.routing_id = po.routing_id
LEFT JOIN prod_work_center wc ON wc.work_center_id = od.work_center_id
WHERE po.production_order_id = :production_order_id
ORDER BY od.sequence_no;


-- =====================================================================================
-- REP-PROD-03. Акт о браке
-- Параметры: :period_from, :period_to
-- Реестр всех операций, не прошедших контроль качества за период —
-- для контролёра/технолога/директора.
-- =====================================================================================

-- Q-PROD-R03
SELECT oe.execution_id,
       od.operation_name,
       wc.work_center_name,
       oe.performed_by_employee_id,
       r->>'quality_point_id' AS quality_point_id,
       qp.quality_point_name,
       r->>'comment'          AS comment,
       oe.end_time
FROM prod_operation_execution oe
JOIN prod_operation_definition od ON od.operation_id = oe.operation_id
LEFT JOIN prod_work_center wc ON wc.work_center_id = oe.work_center_id,
     LATERAL jsonb_array_elements(oe.quality_results_json) AS r
LEFT JOIN prod_quality_point qp ON qp.quality_point_id = (r->>'quality_point_id')
WHERE (r->>'is_passed')::boolean = false
  AND oe.end_time >= :period_from
  AND oe.end_time <  :period_to
ORDER BY oe.end_time;


-- =====================================================================================
-- REP-PROD-04. Отчёт о выполнении производственных заказов
-- Параметры: :period_from, :period_to
-- Сводка по заказам за период: план, статус, доля завершённых нарядов —
-- для директора/планировщика.
-- =====================================================================================

-- Q-PROD-R04
SELECT po.production_order_id,
       b.bom_name,
       r.routing_name,
       po.planned_quantity,
       po.planned_start_date,
       po.planned_end_date,
       po.status_id,
       COUNT(wo.work_order_id) AS work_orders_total,
       COUNT(wo.work_order_id) FILTER (WHERE wo.status_id = 'completed') AS work_orders_completed,
       ROUND(
           100.0 * COUNT(wo.work_order_id) FILTER (WHERE wo.status_id = 'completed')
           / NULLIF(COUNT(wo.work_order_id), 0),
           1
       ) AS completion_percent
FROM prod_production_order po
LEFT JOIN prod_bom     b  ON b.bom_id = po.bom_id
LEFT JOIN prod_routing r  ON r.routing_id = po.routing_id
LEFT JOIN prod_work_order wo ON wo.production_order_id = po.production_order_id
WHERE po.planned_start_date >= :period_from
  AND po.planned_start_date <  :period_to
GROUP BY po.production_order_id, b.bom_name, r.routing_name, po.planned_quantity,
         po.planned_start_date, po.planned_end_date, po.status_id
ORDER BY po.planned_start_date;


-- =====================================================================================
-- REP-PROD-05. Ведомость расхода материалов по заказу
-- Параметр: :production_order_id
-- План (норма BOM × плановое количество) против факта (actual_materials_json по
-- всем нарядам заказа), в количестве и в деньгах (unit_cost) — для планировщика/директора.
-- =====================================================================================

-- Q-PROD-R05
WITH planned AS (
    SELECT po.production_order_id,
           bi.material_id,
           bi.quantity * po.planned_quantity AS planned_quantity,
           bi.unit_cost
    FROM prod_production_order po
    JOIN prod_bom_item bi ON bi.bom_id = po.bom_id
    WHERE po.production_order_id = :production_order_id
),
actual AS (
    SELECT wo.production_order_id,
           m->>'material_id' AS material_id,
           SUM((m->>'quantity')::numeric) AS actual_quantity
    FROM prod_work_order wo,
         LATERAL jsonb_array_elements(wo.actual_materials_json) AS m
    WHERE wo.production_order_id = :production_order_id
    GROUP BY wo.production_order_id, m->>'material_id'
)
SELECT p.material_id,
       p.planned_quantity,
       COALESCE(a.actual_quantity, 0) AS actual_quantity,
       COALESCE(a.actual_quantity, 0) - p.planned_quantity AS variance_quantity,
       p.unit_cost,
       ROUND(p.planned_quantity * p.unit_cost, 2) AS planned_cost,
       ROUND(COALESCE(a.actual_quantity, 0) * p.unit_cost, 2) AS actual_cost,
       ROUND((COALESCE(a.actual_quantity, 0) - p.planned_quantity) * p.unit_cost, 2) AS variance_cost
FROM planned p
LEFT JOIN actual a
       ON a.production_order_id = p.production_order_id
      AND a.material_id = p.material_id
ORDER BY variance_cost DESC NULLS LAST;


-- =====================================================================================
-- REP-PROD-06. Спецификация изделия (BOM)
-- Параметр: :bom_id
-- Печатная форма состава изделия с нормами расхода и плановой стоимостью —
-- для технолога.
-- =====================================================================================

-- Q-PROD-R06
SELECT bi.material_id,
       bi.quantity,
       bi.unit_cost,
       ROUND(bi.quantity * bi.unit_cost, 2) AS line_cost
FROM prod_bom_item bi
WHERE bi.bom_id = :bom_id
ORDER BY bi.material_id;

-- итог по спецификации (сумма line_cost) — вынесен отдельным запросом,
-- т.к. в отчёте это строка "Итого" под таблицей, а не строка данных
SELECT ROUND(SUM(bi.quantity * bi.unit_cost), 2) AS total_cost
FROM prod_bom_item bi
WHERE bi.bom_id = :bom_id;


-- =====================================================================================
-- REP-PROD-07. Отчёт по отклонениям технологических параметров
-- Параметры: :period_from, :period_to
-- Все фактические измерения, вышедшие за допуск целевого параметра операции —
-- для технолога/контролёра.
-- =====================================================================================

-- Q-PROD-R07
SELECT oe.execution_id,
       od.operation_name,
       m->>'parameter_name'            AS parameter_name,
       (m->>'measured_value')::numeric AS measured_value,
       (p->>'target_value')::numeric   AS target_value,
       (p->>'tolerance')::numeric      AS tolerance,
       (m->>'measured_value')::numeric - (p->>'target_value')::numeric AS deviation
FROM prod_operation_execution oe
JOIN prod_operation_definition od ON od.operation_id = oe.operation_id,
     LATERAL jsonb_array_elements(oe.measurements_json) AS m
JOIN LATERAL jsonb_array_elements(od.parameters_json) AS p
     ON p->>'name' = m->>'parameter_name'
WHERE ABS((m->>'measured_value')::numeric - (p->>'target_value')::numeric) > (p->>'tolerance')::numeric
  AND oe.start_time >= :period_from
  AND oe.start_time <  :period_to
ORDER BY oe.start_time;


-- =====================================================================================
-- REP-PROD-08. Отчёт по производительности сотрудников
-- Параметры: :period_from, :period_to
-- Сводка по каждому исполнителю: количество операций, суммарные часы,
-- доля прошедших контроль качества — для мастера/директора.
-- =====================================================================================

-- Q-PROD-R08
WITH exec_hours AS (
    SELECT oe.execution_id,
           oe.performed_by_employee_id,
           EXTRACT(EPOCH FROM (COALESCE(oe.end_time, now()) - oe.start_time)) / 3600.0 AS hours
    FROM prod_operation_execution oe
    WHERE oe.start_time >= :period_from
      AND oe.start_time <  :period_to
),
quality AS (
    SELECT oe.execution_id,
           oe.performed_by_employee_id,
           (r->>'is_passed')::boolean AS is_passed
    FROM prod_operation_execution oe,
         LATERAL jsonb_array_elements(oe.quality_results_json) AS r
    WHERE oe.start_time >= :period_from
      AND oe.start_time <  :period_to
)
SELECT eh.performed_by_employee_id,
       COUNT(DISTINCT eh.execution_id) AS operations_count,
       ROUND(SUM(eh.hours), 1) AS total_hours,
       COUNT(*) FILTER (WHERE q.is_passed = true)  AS passed_count,
       COUNT(*) FILTER (WHERE q.is_passed = false) AS failed_count,
       ROUND(
           100.0 * COUNT(*) FILTER (WHERE q.is_passed = true)
           / NULLIF(COUNT(*), 0),
           1
       ) AS pass_rate_percent
FROM exec_hours eh
LEFT JOIN quality q ON q.execution_id = eh.execution_id
GROUP BY eh.performed_by_employee_id
ORDER BY total_hours DESC;


-- =====================================================================================
-- REP-PROD-09. Себестоимость продукции в динамике (инвестиционный отчет)
-- Параметры: :period_from, :period_to (обычно за 12 месяцев)
-- =====================================================================================

-- Q-PROD-R09
WITH monthly_bom_cost AS (
    SELECT 
        DATE_TRUNC('month', po.planned_start_date) AS month,
        po.bom_id,
        b.bom_name,
        b.product_material_id,
        AVG(bi.quantity * bi.unit_cost) AS material_cost_per_unit
    FROM prod_production_order po
    JOIN prod_bom b ON b.bom_id = po.bom_id
    JOIN prod_bom_item bi ON bi.bom_id = b.bom_id
    WHERE po.planned_start_date >= :period_from
      AND po.planned_start_date <= :period_to
      AND po.status_id = 'completed'
    GROUP BY DATE_TRUNC('month', po.planned_start_date), po.bom_id, b.bom_name, b.product_material_id
),
monthly_labor_cost AS (
    SELECT 
        DATE_TRUNC('month', oe.start_time) AS month,
        po.bom_id,
        AVG(EXTRACT(EPOCH FROM (COALESCE(oe.end_time, now()) - oe.start_time)) / 3600) * 50 AS labor_cost_per_unit  -- 50 у.е./час — ставка
    FROM prod_operation_execution oe
    JOIN prod_work_order wo ON wo.work_order_id = oe.work_order_id
    JOIN prod_production_order po ON po.production_order_id = wo.production_order_id
    WHERE oe.start_time >= :period_from
      AND oe.start_time <= :period_to
    GROUP BY DATE_TRUNC('month', oe.start_time), po.bom_id
),
monthly_overhead AS (
    SELECT 
        DATE_TRUNC('month', po.planned_start_date) AS month,
        po.bom_id,
        AVG(po.overhead_cost) AS overhead_cost_per_unit  -- Если есть поле overhead_cost в prod_production_order
    FROM prod_production_order po
    WHERE po.planned_start_date >= :period_from
      AND po.planned_start_date <= :period_to
      AND po.status_id = 'completed'
    GROUP BY DATE_TRUNC('month', po.planned_start_date), po.bom_id
)
SELECT 
    TO_CHAR(mc.month, 'YYYY-MM') AS month,
    mc.product_material_id,
    mc.bom_name,
    ROUND(mc.material_cost_per_unit, 2) AS material_cost_per_unit,
    ROUND(COALESCE(lc.labor_cost_per_unit, 0), 2) AS labor_cost_per_unit,
    ROUND(COALESCE(oh.overhead_cost_per_unit, 0), 2) AS overhead_cost_per_unit,
    ROUND(mc.material_cost_per_unit + COALESCE(lc.labor_cost_per_unit, 0) + COALESCE(oh.overhead_cost_per_unit, 0), 2) AS total_cost_per_unit,
    -- Предполагаем цену продажи из модуля Sales (вычисляем маржинальность)
    ROUND(
        100 - ((mc.material_cost_per_unit + COALESCE(lc.labor_cost_per_unit, 0) + COALESCE(oh.overhead_cost_per_unit, 0)) / NULLIF(s.avg_selling_price, 0) * 100),
        2
    ) AS margin_percent
FROM monthly_bom_cost mc
LEFT JOIN monthly_labor_cost lc ON lc.month = mc.month AND lc.bom_id = mc.bom_id
LEFT JOIN monthly_overhead oh ON oh.month = mc.month AND oh.bom_id = mc.bom_id
LEFT JOIN (
    SELECT 
        DATE_TRUNC('month', so.order_date) AS month,
        so.material_id,
        AVG(so.unit_price) AS avg_selling_price
    FROM sales_order_line so
    WHERE so.order_date >= :period_from
      AND so.order_date <= :period_to
    GROUP BY DATE_TRUNC('month', so.order_date), so.material_id
) s ON s.month = mc.month AND s.material_id = mc.product_material_id
ORDER BY mc.month, mc.bom_name;