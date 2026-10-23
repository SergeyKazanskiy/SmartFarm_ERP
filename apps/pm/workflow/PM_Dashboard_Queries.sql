-- =====================================================================================
-- PM — запросы для дашбордов
-- =====================================================================================

-- =====================================================================================
-- DASH-PM-01. Проекты и статусы
-- =====================================================================================

-- Q-PM-01-01 (W01-01, Indicator): Активные проекты
SELECT COUNT(*) AS active_projects
FROM pm_project
WHERE status_id IN ('planning', 'active', 'on_hold');

-- Q-PM-01-02 (W01-02, Indicator): Проекты в работе
SELECT COUNT(*) AS in_progress_projects
FROM pm_project
WHERE status_id = 'active';

-- Q-PM-01-03 (W01-03, PieChart): Распределение проектов по статусам
SELECT status_id, COUNT(*) AS project_count
FROM pm_project
GROUP BY status_id
ORDER BY project_count DESC;

-- Q-PM-01-04 (W01-04, Table): Все проекты
SELECT project_id, project_name, project_code, status_id, 
       planned_start_date, planned_end_date, priority
FROM pm_project
ORDER BY priority, planned_start_date;


-- =====================================================================================
-- DASH-PM-02. Этапы и вехи
-- =====================================================================================

-- Q-PM-02-01 (W02-01, Indicator): Этапов в работе
SELECT COUNT(*) AS phases_in_progress
FROM pm_phase
WHERE status_id = 'in_progress';

-- Q-PM-02-02 (W02-02, Indicator): Достигнутые вехи
SELECT COUNT(*) AS achieved_milestones
FROM pm_milestone
WHERE is_achieved = true;

-- Q-PM-02-03 (W02-03, Table): Этапы проекта
SELECT phase_id, phase_name, project_id, planned_start_date, 
       planned_end_date, status_id, completion_percent
FROM pm_phase
WHERE project_id = :project_id
ORDER BY phase_order;


-- =====================================================================================
-- DASH-PM-03. Задачи проекта
-- =====================================================================================

-- Q-PM-03-01 (W03-01, Indicator): Всего задач
SELECT COUNT(*) AS total_tasks
FROM pm_task
WHERE project_id = :project_id;

-- Q-PM-03-02 (W03-02, Indicator): Задач в работе
SELECT COUNT(*) AS tasks_in_progress
FROM pm_task
WHERE project_id = :project_id
  AND status_id = 'in_progress';

-- Q-PM-03-03 (W03-03, Indicator): Просроченных задач
SELECT COUNT(*) AS overdue_tasks
FROM pm_task
WHERE project_id = :project_id
  AND status_id != 'completed'
  AND planned_end_date < CURRENT_DATE;

-- Q-PM-03-04 (W03-04, Table): Задачи с риском срыва сроков
SELECT task_id, task_name, assignee_employee_id, 
       planned_end_date, completion_percent, status_id
FROM pm_task
WHERE project_id = :project_id
  AND status_id != 'completed'
  AND planned_end_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days'
ORDER BY planned_end_date;


-- =====================================================================================
-- DASH-PM-04. Ресурсные потребности
-- =====================================================================================

-- Q-PM-04-01 (W04-01, Indicator): Потребностей в ресурсах
SELECT COUNT(*) AS total_needs
FROM pm_resource_need
WHERE task_id IN (SELECT task_id FROM pm_task WHERE project_id = :project_id);

-- Q-PM-04-02 (W04-02, Indicator): Отправлено в APS
SELECT COUNT(*) AS sent_to_aps
FROM pm_resource_need
WHERE task_id IN (SELECT task_id FROM pm_task WHERE project_id = :project_id)
  AND sent_to_aps = true;

-- Q-PM-04-03 (W04-03, Table): Ресурсные потребности
SELECT resource_need_id, task_id, resource_type, quantity, 
       hours_per_day, days_required, priority, sent_to_aps
FROM pm_resource_need
WHERE task_id IN (SELECT task_id FROM pm_task WHERE project_id = :project_id)
ORDER BY priority;


-- =====================================================================================
-- DASH-PM-05. Бюджет проекта
-- =====================================================================================

-- Q-PM-05-01 (W05-01, Indicator): Общий бюджет проектов
SELECT SUM(total_planned_amount) AS total_budget
FROM pm_budget
WHERE project_id = :project_id;

-- Q-PM-05-02 (W05-02, BarChart): Бюджет по проектам
SELECT project_id, total_planned_amount, total_actual_amount
FROM pm_budget
WHERE project_id = :project_id;

-- Q-PM-05-03 (W05-03, Table): Бюджет проекта
SELECT budget_item_id, category, planned_amount, actual_amount,
       planned_amount - COALESCE(actual_amount, 0) AS variance
FROM pm_budget_item
WHERE budget_id = (SELECT budget_id FROM pm_budget WHERE project_id = :project_id)
ORDER BY category;

-- Q-PM-05-04 (W05-04, Table): Отклонения бюджета
SELECT category, 
       SUM(planned_amount) AS total_planned,
       SUM(COALESCE(actual_amount, 0)) AS total_actual,
       SUM(planned_amount) - SUM(COALESCE(actual_amount, 0)) AS variance
FROM pm_budget_item
WHERE budget_id IN (SELECT budget_id FROM pm_budget WHERE project_id = :project_id)
GROUP BY category;


-- =====================================================================================
-- DASH-PM-06. Риски и изменения
-- =====================================================================================

-- Q-PM-06-01 (W06-01, Indicator): Активных рисков
SELECT COUNT(*) AS active_risks
FROM pm_risk
WHERE project_id = :project_id
  AND status_id NOT IN ('mitigated', 'closed');

-- Q-PM-06-02 (W06-02, Table): Риски проекта
SELECT risk_id, risk_name, probability, impact, severity, 
       status_id, owner_employee_id
FROM pm_risk
WHERE project_id = :project_id
ORDER BY severity DESC;

-- Q-PM-06-03 (W06-03, Table): Запросы на изменение
SELECT change_request_id, title, change_type, status_id, 
       requested_by_employee_id, requested_at
FROM pm_change_request
WHERE project_id = :project_id
ORDER BY requested_at DESC;