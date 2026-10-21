-- =====================================================================================
-- CP — запросы для отчётов
-- =====================================================================================

-- Q-CP-R01: Карточка контрагента
SELECT c.code,
       c.name,
       ct.counterparty_type_name,
       cat.category_name,
       c.tax_id,
       c.phone,
       c.email,
       c.website,
       c.industry,
       c.credit_limit,
       c.payment_terms,
       c.delivery_terms,
       c.status_id
FROM cp_counterparty c
LEFT JOIN cp_counterparty_type ct ON ct.counterparty_type_id = c.counterparty_type_id
LEFT JOIN cp_category cat ON cat.category_id = c.category_id
WHERE c.counterparty_id = :counterparty_id;

-- Q-CP-R02: История взаимодействий
SELECT i.interaction_date,
       i.interaction_type,
       cp.last_name || ' ' || cp.first_name AS contact_person,
       i.employee_id,
       i.subject,
       i.description,
       i.result
FROM cp_interaction i
LEFT JOIN cp_contact_person cp ON cp.contact_id = i.contact_person_id
WHERE i.counterparty_id = :counterparty_id
  AND i.interaction_date >= :period_from
  AND i.interaction_date <= :period_to
ORDER BY i.interaction_date DESC;

-- Q-CP-R03: Реестр договоров
SELECT cp.name AS counterparty_name,
       c.contract_number,
       c.contract_date,
       c.valid_from,
       c.valid_to,
       c.contract_type,
       c.amount,
       c.status_id
FROM cp_contract c
JOIN cp_counterparty cp ON cp.counterparty_id = c.counterparty_id
WHERE c.created_at >= :period_from
  AND c.created_at <= :period_to
ORDER BY cp.name, c.contract_date DESC;

-- Q-CP-R04: Черный список контрагентов
SELECT c.code,
       c.name,
       b.block_date,
       b.reason,
       b.blocked_by_employee_id
FROM cp_blacklist b
JOIN cp_counterparty c ON c.counterparty_id = b.counterparty_id
WHERE b.unblock_date IS NULL
ORDER BY b.block_date DESC;