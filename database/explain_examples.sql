-- =====================================================================
-- File: explain_examples.sql
-- Purpose: Show HOW the indexes in indexes.sql change query plans.
--
--   EXPLAIN          -> the plan MySQL intends to use (does not run the query)
--   EXPLAIN ANALYZE  -> runs the query and reports real time and rows (MySQL 8.0.18+)
--
-- What to look for in classic EXPLAIN output:
--   type = ALL    -> full table scan (reads every row)          BAD for big tables
--   type = range  -> index range scan (e.g. date BETWEEN ...)   GOOD
--   type = ref    -> index lookup on a non-unique value          GOOD
--   type = eq_ref / const -> lookup by primary/unique key        BEST
--   key           -> which index was chosen (NULL = none)
--   rows          -> how many rows MySQL expects to examine
--   Extra: "Using filesort" = an extra sort step; "Using index" = answered from the index alone
-- =====================================================================

-- ---------------------------------------------------------------------
-- Example 1: date-range filter uses idx_orders_order_date
-- ---------------------------------------------------------------------
EXPLAIN
SELECT order_number, order_total
FROM   orders
WHERE  order_date >= '2026-09-01' AND order_date < '2026-09-08';

-- ---------------------------------------------------------------------
-- Example 2: the SAME filter written with a function on the column.
-- MySQL cannot use the index because it would have to compute
-- DATE_FORMAT() for every row first -> full table scan (type = ALL).
-- Rule: keep indexed columns "bare" in WHERE; put functions on the constant side.
-- ---------------------------------------------------------------------
EXPLAIN
SELECT order_number, order_total
FROM   orders
WHERE  DATE(order_date) BETWEEN '2026-09-01' AND '2026-09-07';

-- ---------------------------------------------------------------------
-- Example 3: composite index (customer_id, order_date) answers
-- "orders of one customer, newest first" without a separate sort.
-- ---------------------------------------------------------------------
EXPLAIN ANALYZE
SELECT order_number, order_date, order_total
FROM   orders
WHERE  customer_id = 30
ORDER BY order_date DESC;

-- Same query with the composite index hidden from the optimizer.
-- (INVISIBLE indexes - MySQL 8 - let you test "what if I dropped it?" safely.)
-- When idx_orders_customer_date was created, MySQL silently dropped the index
-- it had auto-created for the customer_id foreign key (the new index starts
-- with customer_id, so it can serve the FK). Hiding it therefore leaves NO
-- index on customer_id: the plan becomes "Table scan" (all rows) + "Sort".
ALTER TABLE orders ALTER INDEX idx_orders_customer_date INVISIBLE;

EXPLAIN ANALYZE
SELECT order_number, order_date, order_total
FROM   orders
WHERE  customer_id = 30
ORDER BY order_date DESC;

ALTER TABLE orders ALTER INDEX idx_orders_customer_date VISIBLE;

-- ---------------------------------------------------------------------
-- Example 4: COVERING index. The query only needs order_id and status, and
-- idx_payments_order_status (order_id, status) contains both, so MySQL answers
-- from the index alone without reading the table rows ("Covering index lookup").
-- ---------------------------------------------------------------------
EXPLAIN
SELECT order_id, COUNT(*)
FROM   payments
WHERE  order_id = 500 AND status = 'COMPLETED'
GROUP BY order_id;

-- ---------------------------------------------------------------------
-- Example 5: a JOIN. For each order row MySQL looks up the customer by
-- PRIMARY KEY (type = eq_ref) instead of scanning customers.
-- ---------------------------------------------------------------------
EXPLAIN
SELECT o.order_number, c.customer_code
FROM   orders o
JOIN   customers c ON c.customer_id = o.customer_id
WHERE  o.order_date >= '2026-09-01' AND o.order_date < '2026-09-08';

-- ---------------------------------------------------------------------
-- Example 6: find which indexes exist and how selective they are
-- (Cardinality = estimated number of distinct values).
-- ---------------------------------------------------------------------
SHOW INDEX FROM orders;
