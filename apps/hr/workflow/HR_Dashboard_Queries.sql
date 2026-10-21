-- =====================================================================================
-- HR — запросы для дашбордов (см. HR_Dashboards_Roles.yml)
-- Диалект: PostgreSQL. Использует HR_Schema.json версии 1.2.
-- Параметры :period_from / :period_to — период отчёта, передаются из UI дашборда.
-- =====================================================================================


-- =====================================================================================
-- DASH-HR-01. Персонал предприятия
-- =====================================================================================

-- Q-HR-01-01 (W01-01, Indicator): Активные сотрудники
SELECT COUNT(*) AS active_employees
FROM hr_employee
WHERE status_id = 'active';

-- Q-HR-01-02 (W01-02, Indicator): Сотрудники в длительном отсутствии
SELECT COUNT(*) AS on_leave_employees
FROM hr_employee
WHERE status_id = 'on_leave';

-- Q-HR-01-03 (W01-03, PieChart): Распределение сотрудников по подразделениям
SELECT d.department_name,
       COUNT(e.employee_id) AS employee_count
FROM hr_employee e
LEFT JOIN core_department d ON d.department_id = e.department_id
WHERE e.status_id = 'active'
GROUP BY d.department_name
ORDER BY employee_count DESC;

-- Q-HR-01-04 (W01-04, Table): Кадровые переводы за период
-- Переводы восстанавливаются из общего аудита (core_audit_log), т.к. отдельного
-- журнала переводов в HR намеренно нет — история изменений ведётся централизованно.
SELECT audit_id, entity_id AS employee_id, operation_date, old_value_json, new_value_json
FROM core_audit_log
WHERE entity_type = 'hr_employee'
  AND operation_type = 'UPDATE'
  AND operation_date >= :period_from
  AND operation_date <  :period_to
ORDER BY operation_date DESC;

-- Q-HR-01-05 (W01-05, Table): Заявки на отсутствие, ожидающие рассмотрения
SELECT a.absence_id,
       e.personnel_number,
       at.absence_type_name,
       a.date_from,
       a.date_to
FROM hr_employee_absence a
JOIN hr_employee e ON e.employee_id = a.employee_id
JOIN hr_absence_type at ON at.absence_type_id = a.absence_type_id
WHERE a.status = 'requested'
ORDER BY a.date_from;


-- =====================================================================================
-- DASH-HR-02. Компетенции и допуски
-- =====================================================================================

-- Q-HR-02-01 (W02-01, Indicator): Навыки, ожидающие подтверждения руководителем
SELECT COUNT(*) AS pending_confirmation
FROM hr_employee_skill
WHERE self_assessed_level IS NOT NULL
  AND confirmed_level IS NULL;

-- Q-HR-02-02 (W02-02, Table): Матрица подтверждённых навыков по подразделению
SELECT d.department_name,
       s.skill_name,
       COUNT(es.employee_skill_id) AS employees_with_skill
FROM hr_employee_skill es
JOIN hr_employee e ON e.employee_id = es.employee_id
JOIN hr_skill s ON s.skill_id = es.skill_id
LEFT JOIN core_department d ON d.department_id = e.department_id
WHERE es.confirmed_level IS NOT NULL
GROUP BY d.department_name, s.skill_name
ORDER BY d.department_name, s.skill_name;

-- Q-HR-02-03 (W02-03, Table): Допуски/медосмотры/удостоверения с истекающим сроком действия
SELECT 'certificate' AS record_kind, ec.employee_id, c.certificate_name AS name, ec.expire_date
FROM hr_employee_certificate ec
JOIN hr_certificate c ON c.certificate_id = ec.certificate_id
WHERE ec.expire_date IS NOT NULL
  AND ec.expire_date <= CURRENT_DATE + INTERVAL '30 days'
UNION ALL
SELECT 'medical_check', mc.employee_id, 'Медосмотр', mc.valid_to
FROM hr_medical_check mc
WHERE mc.valid_to IS NOT NULL
  AND mc.valid_to <= CURRENT_DATE + INTERVAL '30 days'
UNION ALL
SELECT 'driving_license', dl.employee_id, 'Водительское удостоверение', dl.valid_to
FROM hr_driving_license dl
WHERE dl.valid_to IS NOT NULL
  AND dl.valid_to <= CURRENT_DATE + INTERVAL '30 days'
ORDER BY expire_date;

-- Q-HR-02-04 (W02-04, Indicator): Сотрудники без действующей квалификации
SELECT COUNT(*) AS employees_without_valid_qualification
FROM hr_employee e
WHERE e.status_id = 'active'
  AND NOT EXISTS (
      SELECT 1 FROM hr_employee_qualification eq
      WHERE eq.employee_id = e.employee_id
        AND (eq.valid_to IS NULL OR eq.valid_to >= CURRENT_DATE)
  );


-- =====================================================================================
-- DASH-HR-03. Табелирование
-- =====================================================================================

-- Q-HR-03-01 (W03-01, Indicator): Табели, ожидающие утверждения
SELECT COUNT(*) AS pending_timesheets
FROM hr_timesheet
WHERE status_id = 'submitted';

-- Q-HR-03-02 (W03-02, BarChart): Отработанные часы по сотрудникам за период
SELECT employee_id,
       SUM(hours_worked) AS total_hours
FROM hr_timesheet
WHERE status_id = 'approved'
  AND work_date >= :period_from
  AND work_date <  :period_to
GROUP BY employee_id
ORDER BY total_hours DESC
LIMIT 20;

-- Q-HR-03-03 (W03-03, Indicator): Суммарные сверхурочные часы за период
SELECT SUM(overtime_hours) AS total_overtime_hours
FROM hr_timesheet
WHERE status_id = 'approved'
  AND work_date >= :period_from
  AND work_date <  :period_to;



-- =====================================================================================
-- DASH-HR-04. Эффективность персонала (инвестиционная)
-- =====================================================================================

-- Q-HR-04-01 (W04-01, Indicator): Средняя производительность по подразделению
WITH department_hours AS (
    SELECT 
        e.department_id,
        SUM(t.hours_worked) AS total_hours,
        COUNT(DISTINCT t.employee_id) AS employee_count
    FROM hr_timesheet t
    JOIN hr_employee e ON e.employee_id = t.employee_id
    WHERE t.status_id = 'approved'
      AND t.work_date >= :period_from
      AND t.work_date <= :period_to
    GROUP BY e.department_id
)
SELECT 
    ROUND(AVG(total_hours / NULLIF(employee_count, 0)), 2) AS avg_hours_per_employee
FROM department_hours;

-- Q-HR-04-02 (W04-02, Indicator): Средний уровень подтверждённых навыков
SELECT 
    COUNT(*) FILTER (WHERE confirmed_level IS NOT NULL) AS confirmed_skills,
    COUNT(*) AS total_skills,
    ROUND(100.0 * COUNT(*) FILTER (WHERE confirmed_level IS NOT NULL) / NULLIF(COUNT(*), 0), 1) AS confirmation_rate
FROM hr_employee_skill;

-- Q-HR-04-03 (W04-03, BarChart): ТОП-5 сотрудников по продуктивности (score)
SELECT 
    e.employee_id,
    e.personnel_number,
    ROUND(AVG(cs.score_value), 2) AS avg_score
FROM hr_employee_competency_score cs
JOIN hr_employee e ON e.employee_id = cs.employee_id
WHERE cs.evaluated_at >= :period_from
  AND cs.evaluated_at <= :period_to
GROUP BY e.employee_id, e.personnel_number
ORDER BY avg_score DESC
LIMIT 5;

-- Q-HR-04-04 (W04-04, Table): Сотрудники с истекшими квалификациями
SELECT 
    e.employee_id,
    e.personnel_number,
    e.position_id,
    q.qualification_name,
    eq.valid_to,
    (CURRENT_DATE - eq.valid_to) AS days_expired
FROM hr_employee e
JOIN hr_employee_qualification eq ON eq.employee_id = e.employee_id
JOIN hr_qualification q ON q.qualification_id = eq.qualification_id
WHERE e.status_id = 'active'
  AND eq.valid_to < CURRENT_DATE
ORDER BY days_expired DESC;