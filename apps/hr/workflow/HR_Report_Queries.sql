-- =====================================================================================
-- HR — запросы для отчётов (см. HR_Reports_Roles.yml)
-- Диалект: PostgreSQL. Использует HR_Schema.json версии 1.2.
-- Параметры — именованные (:param), совместимы с SQLAlchemy text() в FastAPI.
-- =====================================================================================


-- =====================================================================================
-- REP-HR-01. Личная карточка сотрудника
-- Параметр: :employee_id
-- =====================================================================================

-- Q-HR-R01 (шапка)
SELECT natural_person_id, personnel_number, position_id, department_id,
       employment_date, dismissal_date, status_id
FROM hr_employee
WHERE employee_id = :employee_id;

-- Q-HR-R01 (навыки)
SELECT skill_id, self_assessed_level, confirmed_level
FROM hr_employee_skill
WHERE employee_id = :employee_id;

-- Q-HR-R01 (сертификаты/допуски)
SELECT certificate_id, certificate_number, issue_date, expire_date
FROM hr_employee_certificate
WHERE employee_id = :employee_id;

-- Q-HR-R01 (квалификации)
SELECT qualification_id, valid_to
FROM hr_employee_qualification
WHERE employee_id = :employee_id;


-- =====================================================================================
-- REP-HR-02. Матрица компетенций
-- Параметр: :department_id
-- =====================================================================================

-- Q-HR-R02
SELECT e.employee_id,
       s.skill_name,
       es.self_assessed_level,
       es.confirmed_level,
       (SELECT AVG(cs.score_value)
        FROM hr_employee_competency_score cs
        WHERE cs.employee_id = e.employee_id AND cs.skill_id = s.skill_id) AS score_value
FROM hr_employee_skill es
JOIN hr_employee e ON e.employee_id = es.employee_id
JOIN hr_skill s ON s.skill_id = es.skill_id
WHERE e.department_id = :department_id
ORDER BY e.employee_id, s.skill_name;


-- =====================================================================================
-- REP-HR-03. Реестр истекающих допусков
-- Параметр: :days_threshold (горизонт в днях)
-- =====================================================================================

-- Q-HR-R03
SELECT 'certificate' AS record_kind, ec.employee_id, c.certificate_name AS name, ec.expire_date
FROM hr_employee_certificate ec
JOIN hr_certificate c ON c.certificate_id = ec.certificate_id
WHERE ec.expire_date IS NOT NULL
  AND ec.expire_date <= CURRENT_DATE + (:days_threshold || ' days')::interval
UNION ALL
SELECT 'medical_check', mc.employee_id, 'Медосмотр', mc.valid_to
FROM hr_medical_check mc
WHERE mc.valid_to IS NOT NULL
  AND mc.valid_to <= CURRENT_DATE + (:days_threshold || ' days')::interval
UNION ALL
SELECT 'driving_license', dl.employee_id, 'Водительское удостоверение', dl.valid_to
FROM hr_driving_license dl
WHERE dl.valid_to IS NOT NULL
  AND dl.valid_to <= CURRENT_DATE + (:days_threshold || ' days')::interval
ORDER BY expire_date;


-- =====================================================================================
-- REP-HR-04. Ведомость отсутствий
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-HR-R04
SELECT a.employee_id,
       at.absence_type_name,
       a.date_from,
       a.date_to,
       a.status
FROM hr_employee_absence a
JOIN hr_absence_type at ON at.absence_type_id = a.absence_type_id
WHERE a.date_from >= :period_from
  AND a.date_from <  :period_to
ORDER BY a.date_from;


-- =====================================================================================
-- REP-HR-05. Табель учёта рабочего времени
-- Параметры: :period_from, :period_to, :department_id (необязательный фильтр)
-- =====================================================================================

-- Q-HR-R05
SELECT t.employee_id,
       t.work_date,
       t.hours_worked,
       t.overtime_hours,
       t.status_id
FROM hr_timesheet t
JOIN hr_employee e ON e.employee_id = t.employee_id
WHERE t.work_date >= :period_from
  AND t.work_date <  :period_to
  AND (:department_id IS NULL OR e.department_id = :department_id)
ORDER BY t.employee_id, t.work_date;



-- =====================================================================================
-- REP-HR-06. Анализ эффективности персонала по подразделениям
-- Параметры: :period_from, :period_to
-- =====================================================================================

-- Q-HR-R06
WITH department_employees AS (
    SELECT 
        department_id,
        COUNT(employee_id) AS employee_count
    FROM hr_employee
    WHERE status_id = 'active'
    GROUP BY department_id
),
department_hours AS (
    SELECT 
        e.department_id,
        SUM(t.hours_worked) AS total_hours,
        SUM(t.overtime_hours) AS overtime_hours,
        COUNT(DISTINCT t.employee_id) AS active_employees
    FROM hr_timesheet t
    JOIN hr_employee e ON e.employee_id = t.employee_id
    WHERE t.status_id = 'approved'
      AND t.work_date >= :period_from
      AND t.work_date <= :period_to
    GROUP BY e.department_id
),
department_skills AS (
    SELECT 
        e.department_id,
        COUNT(es.employee_skill_id) FILTER (WHERE es.confirmed_level IS NOT NULL) AS confirmed_skills,
        COUNT(es.employee_skill_id) AS total_skills
    FROM hr_employee_skill es
    JOIN hr_employee e ON e.employee_id = es.employee_id
    GROUP BY e.department_id
),
department_scores AS (
    SELECT 
        e.department_id,
        ROUND(AVG(cs.score_value), 2) AS avg_score
    FROM hr_employee_competency_score cs
    JOIN hr_employee e ON e.employee_id = cs.employee_id
    WHERE cs.evaluated_at >= :period_from
      AND cs.evaluated_at <= :period_to
    GROUP BY e.department_id
)
SELECT 
    d.department_name,
    COALESCE(de.employee_count, 0) AS employee_count,
    COALESCE(dh.total_hours, 0) AS total_hours,
    ROUND(COALESCE(dh.total_hours, 0) / NULLIF(COALESCE(dh.active_employees, 1), 0), 2) AS avg_hours_per_employee,
    COALESCE(dh.overtime_hours, 0) AS overtime_hours,
    ROUND(100.0 * COALESCE(ds.confirmed_skills, 0) / NULLIF(COALESCE(ds.total_skills, 1), 0), 1) AS skill_confirmation_rate,
    COALESCE(dsc.avg_score, 0) AS avg_score
FROM core_department d
LEFT JOIN department_employees de ON de.department_id = d.department_id
LEFT JOIN department_hours dh ON dh.department_id = d.department_id
LEFT JOIN department_skills ds ON ds.department_id = d.department_id
LEFT JOIN department_scores dsc ON dsc.department_id = d.department_id
WHERE COALESCE(de.employee_count, 0) > 0
ORDER BY avg_score DESC;