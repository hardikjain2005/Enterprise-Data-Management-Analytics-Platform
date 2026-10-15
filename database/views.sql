-- =====================================================================
-- File: views.sql
-- Purpose: VIEWS = saved SELECT queries that behave like read-only
--          tables. They hide JOIN/GROUP BY logic so the API, the
--          dashboard and analysts all use the SAME definitions
--          (e.g. one definition of "revenue").
--
-- Business rule used everywhere: revenue = order_total of orders that
-- are NOT cancelled. "Collected" = payments with status COMPLETED.
-- =====================================================================

-- ---------------------------------------------------------------------
-- vw_order_summary: one row per order with customer, employee, items
-- and payment position.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_order_summary AS
SELECT  o.order_id,
        o.order_number,
        o.order_date,
        o.status,
        c.customer_id,
        c.customer_code,
        CONCAT(c.first_name, ' ', c.last_name)            AS customer_name,
        c.segment,
        CONCAT(e.first_name, ' ', e.last_name)            AS handled_by,   -- NULL for online orders
        COALESCE(i.item_count, 0)                         AS item_count,
        o.order_total,
        COALESCE(p.amount_paid, 0)                        AS amount_paid,
        o.order_total - COALESCE(p.amount_paid, 0)        AS balance_due,
        CASE
            WHEN o.status = 'CANCELLED'                       THEN 'NOT_APPLICABLE'
            WHEN COALESCE(p.amount_paid, 0) >= o.order_total  THEN 'PAID'
            WHEN COALESCE(p.amount_paid, 0) > 0               THEN 'PARTIALLY_PAID'
            ELSE 'UNPAID'
        END                                               AS payment_status
FROM    orders o
JOIN    customers c      ON c.customer_id = o.customer_id
LEFT JOIN employees e    ON e.employee_id = o.employee_id
LEFT JOIN (SELECT order_id, COUNT(*) AS item_count
             FROM order_items
            GROUP BY order_id) i ON i.order_id = o.order_id
LEFT JOIN (SELECT order_id, SUM(amount) AS amount_paid
             FROM payments
            WHERE status = 'COMPLETED'
            GROUP BY order_id) p ON p.order_id = o.order_id;

-- ---------------------------------------------------------------------
-- vw_customer_360: one row per customer with lifetime metrics.
-- LEFT JOIN keeps customers who have never ordered (total_orders = 0).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_customer_360 AS
SELECT  c.customer_id,
        c.customer_code,
        CONCAT(c.first_name, ' ', c.last_name)                              AS customer_name,
        c.email,
        c.city,
        c.country,
        c.segment,
        c.signup_date,
        COUNT(o.order_id)                                                   AS total_orders,
        SUM(CASE WHEN o.status = 'CANCELLED' THEN 1 ELSE 0 END)             AS cancelled_orders,
        COALESCE(SUM(CASE WHEN o.status <> 'CANCELLED' THEN o.order_total END), 0) AS total_spent,
        MAX(o.order_date)                                                   AS last_order_date,
        DATEDIFF(CURDATE(), MAX(o.order_date))                              AS days_since_last_order,
        fn_customer_tier(c.customer_id)                                     AS tier
FROM    customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_code, c.first_name, c.last_name, c.email,
         c.city, c.country, c.segment, c.signup_date;

-- ---------------------------------------------------------------------
-- vw_monthly_sales: one row per calendar month.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_monthly_sales AS
SELECT  DATE_FORMAT(order_date, '%Y-%m')                                    AS sales_month,
        COUNT(*)                                                            AS total_orders,
        SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END)               AS cancelled_orders,
        COUNT(DISTINCT customer_id)                                         AS unique_customers,
        SUM(CASE WHEN status <> 'CANCELLED' THEN order_total ELSE 0 END)    AS revenue,
        ROUND(AVG(CASE WHEN status <> 'CANCELLED' THEN order_total END), 2) AS avg_order_value
FROM    orders
GROUP BY DATE_FORMAT(order_date, '%Y-%m');

-- ---------------------------------------------------------------------
-- vw_product_performance: sales per product + rank inside its category
-- (window function RANK() ... OVER (PARTITION BY category ...)).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_product_performance AS
SELECT  t.*,
        RANK() OVER (PARTITION BY t.category ORDER BY t.revenue DESC) AS rank_in_category
FROM (
    SELECT  p.product_id,
            p.sku,
            p.product_name,
            p.category,
            p.unit_price,
            p.stock_quantity,
            COUNT(DISTINCT s.order_id)         AS orders_count,
            COALESCE(SUM(s.quantity), 0)       AS units_sold,
            COALESCE(SUM(s.line_total), 0)     AS revenue
    FROM    products p
    -- only lines of non-cancelled orders; LEFT JOIN keeps unsold products
    LEFT JOIN (SELECT oi.order_id, oi.product_id, oi.quantity, oi.line_total
                 FROM order_items oi
                 JOIN orders o ON o.order_id = oi.order_id
                WHERE o.status <> 'CANCELLED') s ON s.product_id = p.product_id
    GROUP BY p.product_id, p.sku, p.product_name, p.category, p.unit_price, p.stock_quantity
) t;

-- ---------------------------------------------------------------------
-- vw_etl_job_status: each ETL job with its LATEST run.
-- ROW_NUMBER() numbers each job's runs newest-first; rn = 1 is the latest.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_etl_job_status AS
WITH ranked_runs AS (
    SELECT  l.*,
            ROW_NUMBER() OVER (PARTITION BY l.job_id ORDER BY l.started_at DESC, l.execution_id DESC) AS rn
    FROM    etl_execution_logs l
),
run_counts AS (
    SELECT  job_id,
            COUNT(*)                                          AS total_runs,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_runs
    FROM    etl_execution_logs
    GROUP BY job_id
)
SELECT  j.job_id,
        j.job_name,
        s.source_name,
        j.source_file,
        j.target_table,
        COALESCE(rc.total_runs, 0)   AS total_runs,
        COALESCE(rc.failed_runs, 0)  AS failed_runs,
        r.execution_id               AS last_execution_id,
        r.started_at                 AS last_started_at,
        r.ended_at                   AS last_ended_at,
        r.status                     AS last_status,
        r.records_read               AS last_records_read,
        r.records_inserted           AS last_records_inserted,
        r.records_updated            AS last_records_updated,
        r.records_rejected           AS last_records_rejected
FROM    etl_jobs j
JOIN    data_sources s     ON s.source_id = j.source_id
LEFT JOIN ranked_runs r    ON r.job_id = j.job_id AND r.rn = 1
LEFT JOIN run_counts rc    ON rc.job_id = j.job_id;

-- ---------------------------------------------------------------------
-- vw_data_quality_summary: issue counts per table / type / severity.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_data_quality_summary AS
SELECT  table_name,
        issue_type,
        severity,
        COUNT(*)                                                         AS total_issues,
        SUM(CASE WHEN resolution_status = 'OPEN' THEN 1 ELSE 0 END)      AS open_issues,
        MAX(detected_at)                                                 AS last_detected_at
FROM    data_quality_issues
GROUP BY table_name, issue_type, severity;
