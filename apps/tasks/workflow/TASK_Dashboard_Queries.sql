-- =====================================================================================
-- TASK — запросы для дашбордов
-- =====================================================================================

-- =====================================================================================
-- DASH-TASK-01. Мои задачи
-- =====================================================================================

-- Q-TASK-01-01 (W01-01, Indicator): Задачи на мне
SELECT COUNT(*) AS my_tasks
FROM task_assignment
WHERE employee_id = :employee_id
  AND status_id IN ('assigned', 'in_progress');

-- Q-TASK-01-02 (W01-02, Indicator): В работе
SELECT COUNT(*) AS in_progress
FROM task_assignment
WHERE employee_id = :employee_id
  AND status_id = 'in_progress';

-- Q-TASK-01-03 (W01-03, Indicator): Просроченные
SELECT COUNT(*) AS overdue
FROM task_task t
JOIN task_assignment a ON a.task_id = t.task_id
WHERE a.employee_id = :employee_id
  AND t.status_id NOT IN ('completed', 'cancelled')
  AND t.planned_finish < NOW();

-- Q-TASK-01-04 (W01-04, Table): Мои активные задачи
SELECT t.task_id, t.task_name, t.priority, t.planned_start, t.planned_finish,
       t.status_id, t.completion_percent
FROM task_task t
JOIN task_assignment a ON a.task_id = t.task_id
WHERE a.employee_id = :employee_id
  AND t.status_id NOT IN ('completed', 'cancelled')
ORDER BY t.priority, t.planned_finish;


-- =====================================================================================
-- DASH-TASK-02. Все задачи
-- =====================================================================================

-- Q-TASK-02-01 (W02-01, Indicator): Всего задач
SELECT COUNT(*) AS total_tasks
FROM task_task;

-- Q-TASK-02-02 (W02-02, Indicator): Задач в работе
SELECT COUNT(*) AS in_progress_tasks
FROM task_task
WHERE status_id = 'in_progress';

-- Q-TASK-02-03 (W02-03, Indicator): Просроченных задач
SELECT COUNT(*) AS overdue_tasks
FROM task_task
WHERE status_id NOT IN ('completed', 'cancelled')
  AND planned_finish < NOW();

-- Q-TASK-02-04 (W02-04, PieChart): Распределение по статусам
SELECT status_id, COUNT(*) AS task_count
FROM task_task
GROUP BY status_id
ORDER BY task_count DESC;

-- Q-TASK-02-05 (W02-05, Table): Все задачи (срочные)
SELECT t.task_id, t.task_name, t.priority, t.status_id,
       t.planned_start, t.planned_finish,
       a.employee_id AS assigned_to,
       t.completion_percent
FROM task_task t
LEFT JOIN task_assignment a ON a.task_id = t.task_id AND a.status_id IN ('assigned', 'in_progress')
WHERE t.priority <= 2 OR t.priority IS NULL
ORDER BY t.priority, t.planned_finish
LIMIT 50;

-- Q-TASK-02-06 (W02-06, Table): Задачи без исполнителя
SELECT t.task_id, t.task_name, t.status_id, t.planned_start, t.planned_finish
FROM task_task t
WHERE t.status_id IN ('created', 'assigned')
  AND NOT EXISTS (
      SELECT 1 FROM task_assignment a
      WHERE a.task_id = t.task_id
        AND a.status_id IN ('assigned', 'in_progress')
  )
ORDER BY t.planned_start;


-- =====================================================================================
-- DASH-TASK-03. Учёт времени
-- =====================================================================================

-- Q-TASK-03-01 (W03-01, Indicator): Всего часов за неделю
SELECT COALESCE(SUM(hours), 0) AS total_hours
FROM task_time_tracking
WHERE employee_id = :employee_id
  AND date_logged >= CURRENT_DATE - INTERVAL '7 days';

-- Q-TASK-03-02 (W03-02, Table): Мои записи времени
SELECT time_tracking_id, task_id, date_logged, hours, description
FROM task_time_tracking
WHERE employee_id = :employee_id
ORDER BY date_logged DESC
LIMIT 30;

-- Q-TASK-03-03 (W03-03, BarChart): Затраты времени по исполнителям
SELECT employee_id,
       COALESCE(SUM(hours), 0) AS total_hours
FROM task_time_tracking
WHERE date_logged >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY employee_id
ORDER BY total_hours DESC
LIMIT 20;