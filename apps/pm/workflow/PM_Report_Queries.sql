-- =====================================================================================
-- PM — запросы для отчётов
-- =====================================================================================

-- Q-PM-R01: Карточка проекта
SELECT project_name, project_code, description, customer_id,
       project_manager_employee_id, planned_start_date, planned_end_date,
       status_id, priority
FROM pm_project
WHERE project_id = :project_id;

-- Q-PM-R02: Дорожная карта проекта
SELECT phase_name, planned_start_date, planned_end_date,
       status_id, completion_percent
FROM pm_phase
WHERE project_id = :project_id
ORDER BY phase_order;

-- Q-PM-R03: Детализация задач
SELECT t.task_name, p.phase_name, t.assignee_employee_id,
       t.planned_start_date, t.planned_end_date, t.status_id, t.completion_percent
FROM pm_task t
LEFT JOIN pm_phase p ON p.phase_id = t.phase_id
WHERE t.project_id = :project_id
ORDER BY t.planned_start_date;

-- Q-PM-R04: Бюджет проекта
SELECT category, 
       SUM(planned_amount) AS planned_amount,
       SUM(COALESCE(actual_amount, 0)) AS actual_amount,
       SUM(planned_amount) - SUM(COALESCE(actual_amount, 0)) AS variance
FROM pm_budget_item
WHERE budget_id = (SELECT budget_id FROM pm_budget WHERE project_id = :project_id)
GROUP BY category
ORDER BY category;

-- Итог
SELECT SUM(planned_amount) AS total_planned,
       SUM(COALESCE(actual_amount, 0)) AS total_actual,
       SUM(planned_amount) - SUM(COALESCE(actual_amount, 0)) AS total_variance
FROM pm_budget_item
WHERE budget_id = (SELECT budget_id FROM pm_budget WHERE project_id = :project_id);

-- Q-PM-R05: Реестр рисков
SELECT risk_name, probability, impact, severity,
       mitigation_plan, status_id, owner_employee_id
FROM pm_risk
WHERE project_id = :project_id
ORDER BY severity DESC;

-- Q-PM-R06: Отчёт для Orchestrator
SELECT report_date, summary, 
       status_summary_json, budget_summary_json, 
       schedule_summary_json, risks_summary_json
FROM pm_report
WHERE project_id = :project_id
  AND report_type = :report_type
ORDER BY report_date DESC
LIMIT 1;