-- =====================================================================================
-- TASK — запросы для отчётов
-- =====================================================================================

-- Q-TASK-R01: Карточка задачи
SELECT task_name, description, planned_start, planned_finish,
       status_id, completion_percent, priority, work_type,
       estimated_hours, actual_hours
FROM task_task
WHERE task_id = :task_id;

-- Дополнительно: список комментариев
SELECT employee_id, comment_text, created_at
FROM task_comment
WHERE task_id = :task_id
ORDER BY created_at;

-- Дополнительно: список фото
SELECT photo_url, description, created_at
FROM task_photo
WHERE task_id = :task_id
ORDER BY created_at;

-- Дополнительно: учёт времени
SELECT date_logged, hours, description
FROM task_time_tracking
WHERE task_id = :task_id
ORDER BY date_logged;

-- Q-TASK-R02: Отчёт по времени
SELECT t.task_id, t.task_name, tt.date_logged, tt.hours, tt.description
FROM task_time_tracking tt
JOIN task_task t ON t.task_id = tt.task_id
WHERE tt.employee_id = :employee_id
  AND tt.date_logged >= :period_from
  AND tt.date_logged <= :period_to
ORDER BY tt.date_logged;

-- Итог
SELECT COALESCE(SUM(hours), 0) AS total_hours
FROM task_time_tracking
WHERE employee_id = :employee_id
  AND date_logged >= :period_from
  AND date_logged <= :period_to;

-- Q-TASK-R03: Реестр задач
SELECT t.task_id, t.task_name, t.priority, t.status_id,
       a.employee_id AS assigned_to,
       t.planned_start, t.planned_finish, t.completion_percent
FROM task_task t
LEFT JOIN task_assignment a ON a.task_id = t.task_id AND a.status_id IN ('assigned', 'in_progress')
WHERE t.created_at >= :period_from
  AND t.created_at <= :period_to
ORDER BY t.priority, t.planned_start;

-- Q-TASK-R04: Анализ загрузки исполнителей
WITH employee_tasks AS (
    SELECT 
        a.employee_id,
        COUNT(DISTINCT t.task_id) AS total_tasks,
        COUNT(DISTINCT t.task_id) FILTER (WHERE t.status_id = 'completed') AS completed_tasks,
        ROUND(100.0 * COUNT(DISTINCT t.task_id) FILTER (WHERE t.status_id = 'completed') / NULLIF(COUNT(DISTINCT t.task_id), 0), 1) AS completion_rate
    FROM task_assignment a
    JOIN task_task t ON t.task_id = a.task_id
    WHERE a.assigned_at >= :period_from
      AND a.assigned_at <= :period_to
    GROUP BY a.employee_id
),
employee_hours AS (
    SELECT 
        employee_id,
        COALESCE(SUM(hours), 0) AS total_hours
    FROM task_time_tracking
    WHERE date_logged >= :period_from
      AND date_logged <= :period_to
    GROUP BY employee_id
)
SELECT 
    et.employee_id,
    et.total_tasks,
    et.completed_tasks,
    et.completion_rate,
    COALESCE(eh.total_hours, 0) AS total_hours
FROM employee_tasks et
LEFT JOIN employee_hours eh ON eh.employee_id = et.employee_id
ORDER BY et.completion_rate DESC;