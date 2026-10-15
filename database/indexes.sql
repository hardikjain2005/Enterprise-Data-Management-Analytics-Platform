-- =====================================================================
-- File: indexes.sql
-- Purpose: Secondary indexes chosen from the ACTUAL query patterns of
--          the API, the views and queries.sql.
--
-- Already created automatically (not repeated here):
--   * PRIMARY KEY  -> clustered index on every table (InnoDB stores rows in PK order)
--   * UNIQUE       -> unique index (customer_code, email, sku, order_number,
--                     payment_reference, (order_id, product_id), ...)
--   * FOREIGN KEY  -> InnoDB needs an index on every FK column and creates
--                     one if none exists. When a composite index below starts
--                     with the FK column, MySQL can use it for the FK instead.
-- =====================================================================

-- ---------------------------------------------------------------------
-- orders
-- ---------------------------------------------------------------------
-- Pattern: monthly sales, date-range filters on the Orders page, dashboard
--   WHERE order_date >= ? AND order_date < ?
CREATE INDEX idx_orders_order_date ON orders (order_date);

-- Pattern: "order history of one customer, newest first"
--   WHERE customer_id = ? ORDER BY order_date DESC
-- Composite: equality column first, then the range/sort column.
-- It also serves the fk_orders_customer foreign key.
CREATE INDEX idx_orders_customer_date ON orders (customer_id, order_date);

-- Pattern: "orders in status X during a period" (Orders page filter,
-- status breakdown per month). status alone has only 5 values (low
-- selectivity), so it is paired with order_date.
CREATE INDEX idx_orders_status_date ON orders (status, order_date);

-- ---------------------------------------------------------------------
-- payments
-- ---------------------------------------------------------------------
-- Pattern: "how much has been paid for this order?" (fn_order_balance,
-- vw_order_summary): WHERE order_id = ? AND status = 'COMPLETED'
-- Also serves the fk_payments_order foreign key.
CREATE INDEX idx_payments_order_status ON payments (order_id, status);

-- Pattern: payments received per day/month, Payments page date filter.
CREATE INDEX idx_payments_payment_date ON payments (payment_date);

-- ---------------------------------------------------------------------
-- order_items
-- ---------------------------------------------------------------------
-- (order_id, product_id) is already UNIQUE, which covers "items of an order".
-- Pattern: "sales of one product" (product performance) needs product_id first.
-- (Serves fk_order_items_product too.)
CREATE INDEX idx_order_items_product ON order_items (product_id);

-- ---------------------------------------------------------------------
-- products / customers
-- ---------------------------------------------------------------------
-- Pattern: Products page filter + revenue by category.
CREATE INDEX idx_products_category ON products (category);

-- Pattern: Customers page filter by segment, new-customer counts by month.
CREATE INDEX idx_customers_segment ON customers (segment);
CREATE INDEX idx_customers_signup_date ON customers (signup_date);

-- ---------------------------------------------------------------------
-- ETL + monitoring tables
-- ---------------------------------------------------------------------
-- Pattern: "latest runs of job X" (ETL page, vw_etl_job_status)
CREATE INDEX idx_etl_logs_job_started ON etl_execution_logs (job_id, started_at);
-- Pattern: dashboard "failed runs" count
CREATE INDEX idx_etl_logs_status ON etl_execution_logs (status);

-- Pattern: Data Quality page: open issues, filtered by severity
CREATE INDEX idx_dq_status_severity ON data_quality_issues (resolution_status, severity);
-- Pattern: issues for one table / issue type (summary charts)
CREATE INDEX idx_dq_table_type ON data_quality_issues (table_name, issue_type);

-- Pattern: "full change history of one record"
--   WHERE table_name = ? AND record_id = ? ORDER BY changed_at
CREATE INDEX idx_audit_table_record ON audit_logs (table_name, record_id, changed_at);
-- Pattern: "what changed recently?"
CREATE INDEX idx_audit_changed_at ON audit_logs (changed_at);

-- Deliberately NOT indexed (examples to discuss in an interview):
--   * customers.is_active / products.is_active -> only 2 values, an index
--     would rarely be chosen by the optimizer and just slows writes.
--   * staging tables -> rewritten every run; the extra write cost is not
--     worth it for a few thousand rows that are read once.
