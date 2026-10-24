-- =====================================================================================
-- Production — запросы для дашбордов (см. Production_Dashboards_Roles.yml)
-- Диалект: PostgreSQL. Коды запросов соответствуют query_ref в YAML-файле ролей.
--
-- ПРЕДПОЛОЖЕНИЕ ПО ТИПАМ ДАННЫХ: *_json-поля (resources_json, parameters_json,
-- measurements_json, quality_results_json, actual_materials_json) объявлены в схеме
-- как text. Для дашбордов ниже они используются как JSON — либо приведением ::jsonb
-- прямо в запросе (как сделано ниже), либо, что правильнее для продакшена,
-- миграцией колонок в нативный jsonb:
--
--   ALTER TABLE prod_operation_definition  ALTER COLUMN resources_json        TYPE jsonb USING resources_json::jsonb;
--   ALTER TABLE prod_operation_definition  ALTER COLUMN parameters_json       TYPE jsonb USING parameters_json::jsonb;
--   ALTER TABLE prod_operation_execution   ALTER COLUMN measurements_json     TYPE jsonb USING measurements_json::jsonb;
--   ALTER TABLE prod_operation_execution   ALTER COLUMN quality_results_json  TYPE jsonb USING quality_results_json::jsonb;
--   ALTER TABLE prod_work_order            ALTER COLUMN actual_materials_json TYPE jsonb USING actual_materials_json::jsonb;
--
-- РЕКОМЕНДУЕМОЕ ДОПОЛНЕНИЕ (только для полноценной стоимостной аналитики,
-- в этом файле НЕ используется, кроме как в комментарии к Q-PROD-08):
--   ALTER TABLE prod_bom_item ADD COLUMN IF NOT EXISTS unit_cost numeric(15,4);
--
-- Параметры :period_from / :period_to — период отчёта, передаются из UI дашборда.
-- =====================================================================================


-- =====================================================================================
-- DASH-PROD-01. Производственные заказы
-- =====================================================================================

-- Q-PROD-01-01 (W01-01, Indicator): Активные заказы
SELECT COUNT(*) AS active_orders
FROM prod_production_order
WHERE status_id IN ('confirmed', 'in_progress');

-- Q-PROD-01-02 (W01-02, Indicator): Просроченные заказы
SELECT COUNT(*) AS overdue_orders
FROM prod_production_order
WHERE status_id IN ('confirmed', 'in_progress')
  AND planned_end_date < CURRENT_DATE;

-- Q-PROD-01-03 (W01-03, PieChart): Распределение заказов по статусам
SELECT status_id, COUNT(*) AS order_count
FROM prod_production_order
GROUP BY status_id
ORDER BY order_count DESC;

-- Q-PROD-01-04 (W01-04, Table): Реестр активных заказов
SELECT po.production_order_id,
       b.bom_name,
       r.routing_name,
       po.planned_quantity,
       po.planned_start_date,
       po.planned_end_date,
       po.status_id
FROM prod_production_order po
LEFT JOIN prod_bom     b ON b.bom_id = po.bom_id
LEFT JOIN prod_routing r ON r.routing_id = po.routing_id
WHERE po.status_id IN ('confirmed', 'in_progress')
ORDER BY po.planned_end_date ASC NULLS LAST;


-- =====================================================================================
-- DASH-PROD-02. Выполнение нарядов в срок
-- =====================================================================================

-- Q-PROD-02-01 (W02-01, Indicator): % нарядов, завершённых вовремя
SELECT ROUND(
         100.0 * COUNT(*) FILTER (WHERE actual_finish <= planned_finish)
         / NULLIF(COUNT(*), 0),
         1
       ) AS on_time_percent
FROM prod_work_order
WHERE status_id = 'completed';

-- Q-PROD-02-02 (W02-02, BarChart): ТОП отклонений факт/план по нарядам
SELECT wo.work_order_id,
       po.production_order_id,
       ROUND(EXTRACT(EPOCH FROM (wo.actual_finish - wo.planned_finish)) / 3600.0, 1) AS deviation_hours
FROM prod_work_order wo
JOIN prod_production_order po ON po.production_order_id = wo.production_order_id
WHERE wo.status_id = 'completed'
  AND wo.actual_finish IS NOT NULL
  AND wo.planned_finish IS NOT NULL
ORDER BY deviation_hours DESC
LIMIT 10;

-- Q-PROD-02-03 (W02-03, LineChart): Динамика завершения нарядов по неделям
SELECT date_trunc('week', actual_finish) AS week_start,
       COUNT(*) AS completed_orders
FROM prod_work_order
WHERE status_id = 'completed'
  AND actual_finish >= :period_from
  AND actual_finish <  :period_to
GROUP BY 1
ORDER BY 1;


-- =====================================================================================
-- DASH-PROD-03. Технологическая матрица
-- =====================================================================================

-- Q-PROD-03-01 (W03-01, Indicator): Всего технологических операций
SELECT COUNT(*) AS total_operations
FROM prod_operation_definition;

-- Q-PROD-03-02 (W03-02, Table): Операции и их ресурсные потребности
SELECT od.operation_id,
       r.routing_name,
       od.sequence_no,
       od.operation_name,
       wc.work_center_name,
       od.resources_json
FROM prod_operation_definition od
LEFT JOIN prod_routing      r  ON r.routing_id = od.routing_id
LEFT JOIN prod_work_center  wc ON wc.work_center_id = od.work_center_id
ORDER BY r.routing_name, od.sequence_no;

-- Q-PROD-03-03 (W03-03, PieChart): Доля операций с контролем качества
SELECT
  CASE WHEN qp.operation_id IS NOT NULL THEN 'С контролем качества' ELSE 'Без контроля качества' END AS category,
  COUNT(DISTINCT od.operation_id) AS operation_count
FROM prod_operation_definition od
LEFT JOIN prod_quality_point qp ON qp.operation_id = od.operation_id
GROUP BY 1;


-- =====================================================================================
-- DASH-PROD-04. Спецификации изделий (BOM)
-- =====================================================================================

-- Q-PROD-04-01 (W04-01, Indicator): Количество спецификаций
SELECT COUNT(*) AS bom_count
FROM prod_bom;

-- Q-PROD-04-02 (W04-02, Table): Нормы расхода материалов по спецификациям
SELECT b.bom_id,
       b.bom_name,
       bi.material_id,
       bi.quantity AS consumption_rate
FROM prod_bom_item bi
JOIN prod_bom b ON b.bom_id = bi.bom_id
ORDER BY b.bom_name, bi.material_id;

-- Q-PROD-04-03 (W04-03, BarChart): ТОП изделий по количеству компонентов
SELECT b.bom_name,
       COUNT(bi.bom_item_id) AS component_count
FROM prod_bom b
JOIN prod_bom_item bi ON bi.bom_id = b.bom_id
GROUP BY b.bom_name
ORDER BY component_count DESC
LIMIT 10;


-- =====================================================================================
-- DASH-PROD-05. Контроль качества
-- (используются JSON-функции PostgreSQL: jsonb_array_elements разворачивает
--  quality_results_json — [{"quality_point_id":"...","is_passed":true,"comment":"..."}] —
--  в отдельные строки)
-- =====================================================================================

-- Q-PROD-05-01 (W05-01, Indicator): % операций, не прошедших контроль
SELECT ROUND(
         100.0 * COUNT(*) FILTER (WHERE (r->>'is_passed')::boolean = false)
         / NULLIF(COUNT(*), 0),
         1
       ) AS fail_rate_percent
FROM prod_operation_execution oe,
     LATERAL jsonb_array_elements(oe.quality_results_json::jsonb) AS r
WHERE oe.start_time >= :period_from
  AND oe.start_time <  :period_to;

-- Q-PROD-05-02 (W05-02, PieChart): Годно / Брак
SELECT
  CASE WHEN (r->>'is_passed')::boolean THEN 'Годно' ELSE 'Брак' END AS quality_category,
  COUNT(*) AS result_count
FROM prod_operation_execution oe,
     LATERAL jsonb_array_elements(oe.quality_results_json::jsonb) AS r
WHERE oe.start_time >= :period_from
  AND oe.start_time <  :period_to
GROUP BY 1;

-- Q-PROD-05-03 (W05-03, Heatmap): Карта брака по рабочим центрам
SELECT wc.work_center_name,
       date_trunc('day', oe.start_time) AS day,
       COUNT(*) FILTER (WHERE (r->>'is_passed')::boolean = false) AS defect_count
FROM prod_operation_execution oe
JOIN prod_work_center wc ON wc.work_center_id = oe.work_center_id,
     LATERAL jsonb_array_elements(oe.quality_results_json::jsonb) AS r
WHERE oe.start_time >= :period_from
  AND oe.start_time <  :period_to
GROUP BY wc.work_center_name, day
ORDER BY day;

-- Q-PROD-05-04 (W05-04, Table): Операции с непройденным контролем
SELECT oe.execution_id,
       od.operation_name,
       wc.work_center_name,
       oe.performed_by_employee_id,
       r->>'quality_point_id' AS quality_point_id,
       r->>'comment'          AS comment,
       oe.end_time
FROM prod_operation_execution oe
JOIN prod_operation_definition od ON od.operation_id = oe.operation_id
LEFT JOIN prod_work_center wc ON wc.work_center_id = oe.work_center_id,
     LATERAL jsonb_array_elements(oe.quality_results_json::jsonb) AS r
WHERE (r->>'is_passed')::boolean = false
ORDER BY oe.end_time DESC NULLS LAST
LIMIT 100;


-- =====================================================================================
-- DASH-PROD-06. Анализ технологических параметров
-- (сравнение измеренных значений measurements_json с целевыми/допуском
--  из parameters_json конкретной операции маршрута)
-- =====================================================================================

-- Q-PROD-06-01 (W06-01, Table): Операции с отклонением фактических параметров сверх допуска
SELECT oe.execution_id,
       od.operation_name,
       m->>'parameter_name'          AS parameter_name,
       (m->>'measured_value')::numeric AS measured_value,
       (p->>'target_value')::numeric   AS target_value,
       (p->>'tolerance')::numeric      AS tolerance,
       oe.start_time
FROM prod_operation_execution oe
JOIN prod_operation_definition od ON od.operation_id = oe.operation_id,
     LATERAL jsonb_array_elements(oe.measurements_json::jsonb) AS m
JOIN LATERAL jsonb_array_elements(od.parameters_json::jsonb) AS p
     ON p->>'name' = m->>'parameter_name'
WHERE ABS((m->>'measured_value')::numeric - (p->>'target_value')::numeric) > (p->>'tolerance')::numeric
ORDER BY oe.start_time DESC
LIMIT 100;

-- Q-PROD-06-02 (W06-02, Indicator): Количество отклонений за период
SELECT COUNT(*) AS deviations_count
FROM prod_operation_execution oe,
     LATERAL jsonb_array_elements(oe.measurements_json::jsonb) AS m
JOIN LATERAL jsonb_array_elements(
       (SELECT od.parameters_json::jsonb FROM prod_operation_definition od WHERE od.operation_id = oe.operation_id)
     ) AS p
     ON p->>'name' = m->>'parameter_name'
WHERE ABS((m->>'measured_value')::numeric - (p->>'target_value')::numeric) > (p->>'tolerance')::numeric
  AND oe.start_time >= :period_from
  AND oe.start_time <  :period_to;


-- =====================================================================================
-- DASH-PROD-07. Загруженность рабочих центров
-- (приближённая оценка: суммарное время выполнения операций на центре за период;
--  это НЕ то же самое, что "простой" из TOIR — там учитывается ремонт/поломка
--  конкретного актива, здесь — просто отсутствие выполняемых операций)
-- =====================================================================================

-- Q-PROD-07-01 (W07-01, BarChart): Время выполнения операций по рабочим центрам
SELECT wc.work_center_name,
       ROUND(SUM(EXTRACT(EPOCH FROM (COALESCE(oe.end_time, now()) - oe.start_time)) / 3600.0), 1) AS busy_hours
FROM prod_operation_execution oe
JOIN prod_work_center wc ON wc.work_center_id = oe.work_center_id
WHERE oe.start_time >= :period_from
  AND oe.start_time <  :period_to
GROUP BY wc.work_center_name
ORDER BY busy_hours DESC;

-- Q-PROD-07-02 (W07-02, Table): Выполненные операции по рабочим центрам
SELECT wc.work_center_name,
       od.operation_name,
       oe.performed_by_employee_id,
       oe.start_time,
       oe.end_time,
       oe.status_id
FROM prod_operation_execution oe
JOIN prod_work_center         wc ON wc.work_center_id = oe.work_center_id
JOIN prod_operation_definition od ON od.operation_id = oe.operation_id
WHERE oe.start_time >= :period_from
  AND oe.start_time <  :period_to
ORDER BY oe.start_time DESC;


-- =====================================================================================
-- DASH-PROD-08. Перерасход материалов
-- (сравнение нормы BOM × плановое количество заказа с фактическим расходом
--  из prod_work_order.actual_materials_json; по КОЛИЧЕСТВУ, не по стоимости —
--  для стоимости не хватает цены, см. примечание в шапке файла)
-- =====================================================================================

-- Q-PROD-08-01 (W08-01, BarChart): Перерасход материалов (факт vs норма) по заказам
WITH planned AS (
    SELECT po.production_order_id,
           bi.material_id,
           bi.quantity * po.planned_quantity AS planned_quantity
    FROM prod_production_order po
    JOIN prod_bom_item bi ON bi.bom_id = po.bom_id
),
actual AS (
    SELECT wo.production_order_id,
           m->>'material_id' AS material_id,
           SUM((m->>'quantity')::numeric) AS actual_quantity
    FROM prod_work_order wo,
         LATERAL jsonb_array_elements(wo.actual_materials_json::jsonb) AS m
    GROUP BY wo.production_order_id, m->>'material_id'
)
SELECT p.production_order_id,
       p.material_id,
       p.planned_quantity,
       COALESCE(a.actual_quantity, 0) AS actual_quantity,
       COALESCE(a.actual_quantity, 0) - p.planned_quantity AS overrun_quantity
FROM planned p
LEFT JOIN actual a
       ON a.production_order_id = p.production_order_id
      AND a.material_id = p.material_id
WHERE COALESCE(a.actual_quantity, 0) > p.planned_quantity
ORDER BY overrun_quantity DESC
LIMIT 20;

-- Q-PROD-08-02 (W08-02, Indicator): Количество позиций с перерасходом
WITH planned AS (
    SELECT po.production_order_id,
           bi.material_id,
           bi.quantity * po.planned_quantity AS planned_quantity
    FROM prod_production_order po
    JOIN prod_bom_item bi ON bi.bom_id = po.bom_id
),
actual AS (
    SELECT wo.production_order_id,
           m->>'material_id' AS material_id,
           SUM((m->>'quantity')::numeric) AS actual_quantity
    FROM prod_work_order wo,
         LATERAL jsonb_array_elements(wo.actual_materials_json::jsonb) AS m
    GROUP BY wo.production_order_id, m->>'material_id'
)
SELECT COUNT(*) AS overrun_items_count
FROM planned p
LEFT JOIN actual a
       ON a.production_order_id = p.production_order_id
      AND a.material_id = p.material_id
WHERE COALESCE(a.actual_quantity, 0) > p.planned_quantity;

-- Q-PROD-08-03 (справочно, НЕ в YAML: пример стоимостного варианта W08-01,
-- работает только после ALTER TABLE prod_bom_item ADD COLUMN unit_cost numeric(15,4))
-- WITH planned AS (
--     SELECT po.production_order_id,
--            bi.material_id,
--            bi.quantity * po.planned_quantity AS planned_quantity,
--            bi.unit_cost
--     FROM prod_production_order po
--     JOIN prod_bom_item bi ON bi.bom_id = po.bom_id
-- )
-- SELECT production_order_id,
--        SUM(planned_quantity * unit_cost) AS planned_cost
-- FROM planned
-- GROUP BY production_order_id;


-- =====================================================================================
-- DASH-PROD-09. Эффективность производства (инвестиционная)
-- =====================================================================================

-- Q-PROD-09-01 (W09-01, LineChart): Динамика выполнения плана по месяцам
WITH monthly_plan AS (
    SELECT 
        DATE_TRUNC('month', planned_start_date) AS month,
        SUM(planned_quantity) AS planned_total
    FROM prod_production_order
    WHERE status_id IN ('completed', 'in_progress')
    GROUP BY DATE_TRUNC('month', planned_start_date)
),
monthly_actual AS (
    SELECT 
        DATE_TRUNC('month', actual_finish) AS month,
        SUM(planned_quantity) AS actual_total
    FROM prod_production_order
    WHERE status_id = 'completed'
    GROUP BY DATE_TRUNC('month', actual_finish)
)
SELECT 
    COALESCE(p.month, a.month) AS month,
    ROUND(
        COALESCE(a.actual_total, 0) / NULLIF(p.planned_total, 0) * 100, 
        1
    ) AS plan_completion_percent
FROM monthly_plan p
FULL OUTER JOIN monthly_actual a ON a.month = p.month
ORDER BY month;

-- Q-PROD-09-02 (W09-02, Indicator): Себестоимость единицы продукции (текущий месяц)
WITH current_month_bom AS (
    SELECT 
        po.production_order_id,
        po.bom_id,
        SUM(bi.quantity * bi.unit_cost) AS bom_cost
    FROM prod_production_order po
    JOIN prod_bom_item bi ON bi.bom_id = po.bom_id
    WHERE DATE_TRUNC('month', po.planned_start_date) = DATE_TRUNC('month', CURRENT_DATE)
    GROUP BY po.production_order_id, po.bom_id
)
SELECT 
    ROUND(AVG(bom_cost), 2) AS avg_cost_per_unit
FROM current_month_bom;

-- Q-PROD-09-03 (W09-03, Indicator): OEE (Общая эффективность оборудования)
-- Требует связки с ТОиР (простои) и Production (выработка)
WITH availability AS (
    -- Доступность = (Плановое время работы - Время простоев) / Плановое время работы
    SELECT 
        (SELECT COUNT(*) FROM prod_work_order WHERE status_id = 'completed') * 8 AS planned_hours,  -- 8 часов в смену
        COALESCE(SUM(EXTRACT(EPOCH FROM (COALESCE(dt.end_time, now()) - dt.start_time)) / 3600), 0) AS downtime_hours
    FROM toir_asset_downtime dt
    WHERE dt.start_time >= DATE_TRUNC('month', CURRENT_DATE)
),
performance AS (
    -- Производительность = (Фактическая выработка / Плановая выработка) * 100
    SELECT 
        SUM(planned_quantity) AS planned_output,
        SUM(planned_quantity) FILTER (WHERE status_id = 'completed') AS actual_output
    FROM prod_production_order
    WHERE DATE_TRUNC('month', planned_start_date) = DATE_TRUNC('month', CURRENT_DATE)
),
quality AS (
    -- Качество = (Годные / Всего) * 100
    SELECT 
        COUNT(*) AS total_operations,
        COUNT(*) FILTER (WHERE (r->>'is_passed')::boolean = true) AS passed_operations
    FROM prod_operation_execution oe,
         LATERAL jsonb_array_elements(oe.quality_results_json) AS r
    WHERE oe.start_time >= DATE_TRUNC('month', CURRENT_DATE)
)
SELECT 
    ROUND(
        (
            (SELECT (planned_hours - downtime_hours) / NULLIF(planned_hours, 0) FROM availability) *
            (SELECT actual_output / NULLIF(planned_output, 0) FROM performance) *
            (SELECT passed_operations / NULLIF(total_operations, 0) FROM quality)
        ) * 100,
        2
    ) AS oee_percent;

-- Q-PROD-09-04 (W09-04, BarChart): ТОП-5 продукции по маржинальности
-- Требует: выручка (из продаж) - себестоимость (из BOM)
WITH bom_cost AS (
    SELECT 
        b.bom_id,
        b.bom_name,
        b.product_material_id,
        SUM(bi.quantity * bi.unit_cost) AS material_cost
    FROM prod_bom b
    JOIN prod_bom_item bi ON bi.bom_id = b.bom_id
    GROUP BY b.bom_id, b.bom_name, b.product_material_id
),
sales_data AS (
    SELECT 
        so.material_id,
        SUM(so.quantity * so.unit_price) AS revenue,
        SUM(so.quantity) AS total_sold
    FROM sales_order_line so
    WHERE so.order_date >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '6 months'
    GROUP BY so.material_id
)
SELECT 
    bc.bom_name,
    s.revenue - (bc.material_cost * s.total_sold) AS total_margin,
    ROUND(
        ((s.revenue - (bc.material_cost * s.total_sold)) / NULLIF(s.revenue, 0)) * 100,
        2
    ) AS margin_percent
FROM bom_cost bc
JOIN sales_data s ON s.material_id = bc.product_material_id
ORDER BY total_margin DESC
LIMIT 5;