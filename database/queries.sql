-- =====================================================================
-- File: queries.sql
-- Purpose: 32 analysis queries, from beginner to advanced.
-- Detailed explanations (what / why / syntax / interview questions) are
-- in docs/SQL_EXPLANATION.md - the numbers match (Q1, Q2, ...).
--
-- Business rule: revenue = order_total of orders that are NOT cancelled.
-- =====================================================================


-- =====================================================================
-- PART A: BASICS (SELECT, WHERE, ORDER BY, DISTINCT, aggregates)
-- =====================================================================

-- Q1. Corporate customers from Maharashtra, newest first
SELECT customer_code, first_name, last_name, city, signup_date
FROM   customers
WHERE  segment = 'Corporate'
  AND  state = 'Maharashtra'
ORDER BY signup_date DESC;

-- Q2. Which cities do our customers come from? (each city once)
SELECT DISTINCT city, country
FROM   customers
ORDER BY country, city;

-- Q3. Overall sales KPIs
SELECT COUNT(*)                   AS total_orders,
       SUM(order_total)           AS total_revenue,
       ROUND(AVG(order_total), 2) AS avg_order_value,
       MIN(order_total)           AS smallest_order,
       MAX(order_total)           AS largest_order
FROM   orders
WHERE  status <> 'CANCELLED';

-- Q4. Number of orders and value per status
SELECT status,
       COUNT(*)         AS orders,
       SUM(order_total) AS total_value
FROM   orders
GROUP BY status
ORDER BY orders DESC;

-- Q5. Customers with more than 15 orders (GROUP BY + HAVING)
SELECT customer_id,
       COUNT(*) AS order_count
FROM   orders
WHERE  status <> 'CANCELLED'          -- WHERE filters ROWS before grouping
GROUP BY customer_id
HAVING COUNT(*) > 15                  -- HAVING filters GROUPS after grouping
ORDER BY order_count DESC;

-- Q6. Revenue per year and quarter (date functions)
SELECT YEAR(order_date)    AS order_year,
       QUARTER(order_date) AS order_quarter,
       COUNT(*)            AS orders,
       SUM(order_total)    AS revenue
FROM   orders
WHERE  status <> 'CANCELLED'
GROUP BY YEAR(order_date), QUARTER(order_date)
ORDER BY order_year, order_quarter;

-- Q7. Which weekday gets the most orders?
SELECT DAYNAME(order_date)  AS weekday,
       COUNT(*)             AS orders
FROM   orders
GROUP BY DAYOFWEEK(order_date), DAYNAME(order_date)
ORDER BY DAYOFWEEK(order_date);


-- =====================================================================
-- PART B: JOINS
-- =====================================================================

-- Q8. INNER JOIN: latest 10 orders with the customer's name
SELECT o.order_number,
       o.order_date,
       CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
       o.status,
       o.order_total
FROM   orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
ORDER BY o.order_date DESC
LIMIT 10;

-- Q9. LEFT JOIN: customers who have NEVER placed an order
SELECT c.customer_code,
       CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
       c.signup_date
FROM   customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE  o.order_id IS NULL;

-- Q10. Multi-table JOIN: every product line of one order
SELECT o.order_number,
       CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
       p.product_name,
       p.category,
       oi.quantity,
       oi.unit_price,
       oi.discount_pct,
       oi.line_total
FROM   orders o
JOIN   customers   c  ON c.customer_id = o.customer_id
JOIN   order_items oi ON oi.order_id   = o.order_id
JOIN   products    p  ON p.product_id  = oi.product_id
WHERE  o.order_number = 'ORD-100010';

-- Q11. SELF JOIN: each employee with their manager
SELECT CONCAT(e.first_name, ' ', e.last_name)  AS employee,
       e.job_title,
       d.department_name,
       COALESCE(CONCAT(m.first_name, ' ', m.last_name), '(top level)') AS manager
FROM   employees e
JOIN   departments d ON d.department_id = e.department_id
LEFT JOIN employees m ON m.employee_id = e.manager_id
ORDER BY d.department_name, e.employee_id;

-- Q12. Revenue handled by each sales employee
SELECT e.employee_code,
       CONCAT(e.first_name, ' ', e.last_name) AS employee,
       COUNT(o.order_id)                     AS orders_handled,
       COALESCE(SUM(o.order_total), 0)       AS revenue_handled
FROM   employees e
JOIN   departments d ON d.department_id = e.department_id
LEFT JOIN orders o   ON o.employee_id = e.employee_id
                    AND o.status <> 'CANCELLED'     -- condition in ON keeps employees with 0 orders
WHERE  d.department_name = 'Sales'
GROUP BY e.employee_id, e.employee_code, e.first_name, e.last_name
ORDER BY revenue_handled DESC;

-- Q13. Products that have never been sold (NOT EXISTS)
SELECT p.sku, p.product_name, p.category, p.stock_quantity
FROM   products p
WHERE  NOT EXISTS (SELECT 1
                   FROM   order_items oi
                   WHERE  oi.product_id = p.product_id);


-- =====================================================================
-- PART C: SUBQUERIES, CASE, COALESCE, CONDITIONAL AGGREGATION
-- =====================================================================

-- Q14. CORRELATED SUBQUERY: products priced above their category's average
SELECT p.sku, p.product_name, p.category, p.unit_price
FROM   products p
WHERE  p.unit_price > (SELECT AVG(p2.unit_price)
                       FROM   products p2
                       WHERE  p2.category = p.category)   -- refers to the outer row
ORDER BY p.category, p.unit_price DESC;

-- Q15. SUBQUERY with IN: Corporate customers who have bought at least one laptop
SELECT customer_code, first_name, last_name, segment
FROM   customers
WHERE  segment = 'Corporate'
  AND  customer_id IN (SELECT o.customer_id
                       FROM   orders o
                       JOIN   order_items oi ON oi.order_id = o.order_id
                       JOIN   products p     ON p.product_id = oi.product_id
                       WHERE  p.category = 'Laptops');

-- Q16. DERIVED TABLE (subquery in FROM): average number of lines per order
SELECT ROUND(AVG(line_count), 2) AS avg_lines_per_order,
       MAX(line_count)           AS max_lines_in_an_order
FROM  (SELECT order_id, COUNT(*) AS line_count
       FROM   order_items
       GROUP BY order_id) AS per_order;

-- Q17. CASE: group orders into value bands
SELECT CASE
           WHEN order_total <  25000  THEN '1. Small  (< 25K)'
           WHEN order_total < 100000  THEN '2. Medium (25K - 1L)'
           WHEN order_total < 500000  THEN '3. Large  (1L - 5L)'
           ELSE                            '4. Very large (5L+)'
       END              AS value_band,
       COUNT(*)         AS orders,
       SUM(order_total) AS revenue
FROM   orders
WHERE  status <> 'CANCELLED'
GROUP BY value_band
ORDER BY value_band;

-- Q18. COALESCE: online orders vs orders handled by a sales person
SELECT COALESCE(CONCAT(e.first_name, ' ', e.last_name), 'Online (self-service)') AS channel,
       COUNT(*) AS orders
FROM   orders o
LEFT JOIN employees e ON e.employee_id = o.employee_id
GROUP BY channel
ORDER BY orders DESC;

-- Q19. CONDITIONAL AGGREGATION (pivot): order statuses per month as columns
SELECT DATE_FORMAT(order_date, '%Y-%m')                         AS month,
       COUNT(*)                                                 AS total,
       SUM(CASE WHEN status = 'DELIVERED'  THEN 1 ELSE 0 END)   AS delivered,
       SUM(CASE WHEN status = 'SHIPPED'    THEN 1 ELSE 0 END)   AS shipped,
       SUM(CASE WHEN status = 'PROCESSING' THEN 1 ELSE 0 END)   AS processing,
       SUM(CASE WHEN status = 'PENDING'    THEN 1 ELSE 0 END)   AS pending,
       SUM(CASE WHEN status = 'CANCELLED'  THEN 1 ELSE 0 END)   AS cancelled,
       ROUND(100 * SUM(status = 'CANCELLED') / COUNT(*), 1)     AS cancel_rate_pct
FROM   orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m')
ORDER BY month;


-- =====================================================================
-- PART D: CTEs AND WINDOW FUNCTIONS
-- =====================================================================

-- Q20. CTE: each customer's spend compared with their segment's average
WITH customer_spend AS (
    SELECT c.customer_id,
           c.customer_code,
           c.segment,
           COALESCE(SUM(o.order_total), 0) AS total_spent
    FROM   customers c
    LEFT JOIN orders o ON o.customer_id = c.customer_id AND o.status <> 'CANCELLED'
    GROUP BY c.customer_id, c.customer_code, c.segment
),
segment_avg AS (
    SELECT segment, AVG(total_spent) AS avg_spent
    FROM   customer_spend
    GROUP BY segment
)
SELECT cs.customer_code,
       cs.segment,
       cs.total_spent,
       ROUND(sa.avg_spent, 2)                     AS segment_avg,
       ROUND(cs.total_spent / sa.avg_spent, 2)    AS times_segment_avg
FROM   customer_spend cs
JOIN   segment_avg sa ON sa.segment = cs.segment
WHERE  cs.total_spent > 2 * sa.avg_spent           -- customers spending 2x their segment's average
ORDER BY times_segment_avg DESC;

-- Q21. ROW_NUMBER: each customer's most recent order
WITH ranked AS (
    SELECT o.customer_id,
           o.order_number,
           o.order_date,
           o.order_total,
           ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date DESC) AS rn
    FROM   orders o
)
SELECT c.customer_code, r.order_number, r.order_date, r.order_total
FROM   ranked r
JOIN   customers c ON c.customer_id = r.customer_id
WHERE  r.rn = 1
ORDER BY r.order_date DESC
LIMIT 20;

-- Q22. DENSE_RANK: top 3 products by revenue in every category
WITH product_revenue AS (
    SELECT p.category,
           p.product_name,
           SUM(oi.line_total) AS revenue
    FROM   order_items oi
    JOIN   products p ON p.product_id = oi.product_id
    JOIN   orders o   ON o.order_id = oi.order_id
    WHERE  o.status <> 'CANCELLED'
    GROUP BY p.category, p.product_name
),
ranked AS (
    SELECT pr.*,
           DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS rnk
    FROM   product_revenue pr
)
SELECT category, rnk, product_name, revenue
FROM   ranked
WHERE  rnk <= 3
ORDER BY category, rnk;

-- Q23. RUNNING TOTAL: cumulative revenue month by month
SELECT sales_month,
       revenue,
       SUM(revenue) OVER (ORDER BY sales_month) AS cumulative_revenue
FROM   vw_monthly_sales
ORDER BY sales_month;

-- Q24. LAG: month-over-month revenue growth
SELECT sales_month,
       revenue,
       LAG(revenue) OVER (ORDER BY sales_month)                       AS previous_month,
       ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY sales_month))
                 / LAG(revenue) OVER (ORDER BY sales_month), 1)       AS growth_pct
FROM   vw_monthly_sales
ORDER BY sales_month;

-- Q25. NTILE: split customers into 4 spending quartiles
SELECT spend_quartile,
       COUNT(*)          AS customers,
       MIN(total_spent)  AS min_spent,
       MAX(total_spent)  AS max_spent
FROM  (SELECT customer_id,
              total_spent,
              NTILE(4) OVER (ORDER BY total_spent DESC) AS spend_quartile
       FROM   vw_customer_360
       WHERE  total_orders > 0) q
GROUP BY spend_quartile
ORDER BY spend_quartile;

-- Q26. RECURSIVE CTE: the reporting chain (org chart) of the company
WITH RECURSIVE org_chart AS (
    SELECT employee_id, CONCAT(first_name, ' ', last_name) AS employee, manager_id,
           1 AS level, CAST(CONCAT(first_name, ' ', last_name) AS CHAR(500)) AS reporting_path
    FROM   employees
    WHERE  manager_id IS NULL                              -- anchor: top-level managers
    UNION ALL
    SELECT e.employee_id, CONCAT(e.first_name, ' ', e.last_name), e.manager_id,
           oc.level + 1, CONCAT(oc.reporting_path, ' > ', e.first_name, ' ', e.last_name)
    FROM   employees e
    JOIN   org_chart oc ON e.manager_id = oc.employee_id   -- recursive step: their reports
)
SELECT level, employee, reporting_path
FROM   org_chart
ORDER BY reporting_path;


-- =====================================================================
-- PART E: DATA QUALITY & ETL MONITORING
-- =====================================================================

-- Q27. Possible duplicate customers: same name in the same city
SELECT first_name, last_name, city,
       COUNT(*)                                    AS records,
       GROUP_CONCAT(customer_code ORDER BY customer_code) AS customer_codes
FROM   customers
GROUP BY first_name, last_name, city
HAVING COUNT(*) > 1;

-- Q28. Reconciliation: does order_total equal the sum of its lines?
--      (proves the trigger works - should return 0 rows)
SELECT o.order_number, o.order_total, SUM(oi.line_total) AS lines_total
FROM   orders o
JOIN   order_items oi ON oi.order_id = o.order_id
GROUP BY o.order_id, o.order_number, o.order_total
HAVING o.order_total <> SUM(oi.line_total);

-- Q29. ETL success rate and volume per job
SELECT j.job_name,
       COUNT(*)                                                     AS runs,
       SUM(l.status = 'SUCCESS')                                    AS successful,
       SUM(l.status = 'PARTIAL_SUCCESS')                            AS partial,
       SUM(l.status = 'FAILED')                                     AS failed,
       SUM(l.records_read)                                          AS rows_read,
       SUM(l.records_rejected)                                      AS rows_rejected,
       ROUND(100 * SUM(l.records_rejected) / NULLIF(SUM(l.records_read), 0), 2) AS reject_rate_pct,
       ROUND(AVG(TIMESTAMPDIFF(MICROSECOND, l.started_at, l.ended_at)) / 1000000, 2) AS avg_seconds
FROM   etl_execution_logs l
JOIN   etl_jobs j ON j.job_id = l.job_id
GROUP BY j.job_id, j.job_name
ORDER BY j.job_id;

-- Q30. Open data-quality issues by severity (most severe first)
SELECT severity,
       COUNT(*)                     AS open_issues,
       COUNT(DISTINCT table_name)   AS tables_affected
FROM   data_quality_issues
WHERE  resolution_status = 'OPEN'
GROUP BY severity
ORDER BY FIELD(severity, 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW');

-- Q31. Payment reconciliation per month: billed vs collected
SELECT DATE_FORMAT(o.order_date, '%Y-%m')                            AS month,
       SUM(o.order_total)                                            AS billed,
       SUM(COALESCE(p.paid, 0))                                      AS collected,
       SUM(o.order_total) - SUM(COALESCE(p.paid, 0))                 AS outstanding,
       ROUND(100 * SUM(COALESCE(p.paid, 0)) / SUM(o.order_total), 1) AS collection_rate_pct
FROM   orders o
LEFT JOIN (SELECT order_id, SUM(amount) AS paid
           FROM   payments
           WHERE  status = 'COMPLETED'
           GROUP BY order_id) p ON p.order_id = o.order_id
WHERE  o.status <> 'CANCELLED'
GROUP BY DATE_FORMAT(o.order_date, '%Y-%m')
ORDER BY month;


-- =====================================================================
-- PART F: USING VIEWS, FUNCTIONS AND PROCEDURES
-- =====================================================================

-- Q32. Top 10 customers using the view + stored functions
SELECT customer_code,
       customer_name,
       segment,
       total_orders,
       total_spent,
       tier,
       fn_customer_total_spent(customer_id) AS spent_via_function   -- same number, from the function
FROM   vw_customer_360
ORDER BY total_spent DESC
LIMIT 10;

-- Stored procedures are run with CALL:
CALL sp_get_customer_summary(1);
CALL sp_sales_report('2026-01-01', '2026-04-01');      -- Jan..Mar 2026 (end date exclusive)
