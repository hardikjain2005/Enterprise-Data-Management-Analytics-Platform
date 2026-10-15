# SQL Learning Guide (using this project's database)

Every example runs on this project's MySQL database. Open a SQL prompt with:

```bash
mysql -h 127.0.0.1 -u edp_app -p enterprise_data_platform
```

How to use this guide: read the explanation, run the example, **try the practice question yourself**, then check the answer.

Tables you will use most:
`customers`, `products`, `orders` (order header), `order_items` (one row per product in an order), `payments`,
`employees`, `departments`, `etl_execution_logs`, `data_quality_issues`.

---

## 1. SELECT - choose columns

**Idea:** `SELECT` says *which columns* you want, `FROM` says *which table*.

```sql
SELECT column1, column2 FROM table_name;
SELECT * FROM table_name;          -- * = all columns (fine for exploring, avoid in application code)
```

**Example from the project**
```sql
SELECT customer_code, first_name, last_name, email
FROM   customers
LIMIT  5;                          -- only the first 5 rows
```

You can also compute and rename columns with `AS` (an **alias**):
```sql
SELECT product_name, unit_price, unit_price * 1.18 AS price_with_gst
FROM   products
LIMIT  5;
```

**Practice:** Show the `sku`, `product_name` and `stock_quantity` of all products.

<details><summary>Answer</summary>

```sql
SELECT sku, product_name, stock_quantity
FROM   products;
```
</details>

---

## 2. WHERE - choose rows

**Idea:** `WHERE` keeps only rows for which the condition is TRUE.

Operators: `=  <>  <  >  <=  >=`, `AND`, `OR`, `NOT`, `IN (...)`, `BETWEEN a AND b`, `LIKE 'pat%'`, `IS NULL`.

```sql
SELECT columns FROM table WHERE condition;
```

**Example**
```sql
SELECT order_number, status, order_total
FROM   orders
WHERE  status IN ('PENDING', 'PROCESSING')
  AND  order_total > 100000;
```

`LIKE` patterns: `%` = any characters, `_` = exactly one character.
```sql
SELECT first_name, last_name, email FROM customers WHERE email LIKE '%@gmail.com';
```

`NULL` means "unknown / no value". You must test it with `IS NULL`, never `= NULL`:
```sql
SELECT order_number FROM orders WHERE employee_id IS NULL LIMIT 5;   -- online orders
```

**Practice:** Find products in the `Laptops` category that cost less than ₹70,000.

<details><summary>Answer</summary>

```sql
SELECT sku, product_name, unit_price
FROM   products
WHERE  category = 'Laptops'
  AND  unit_price < 70000;
```
</details>

---

## 3. ORDER BY - sort

**Idea:** `ORDER BY col ASC` (default, smallest first) or `DESC` (largest first). Several columns = tie-breakers.
`LIMIT n` keeps the first n rows *after* sorting.

```sql
SELECT ... FROM ... ORDER BY col1 DESC, col2 ASC LIMIT 10;
```

**Example** - the 5 most expensive products:
```sql
SELECT product_name, unit_price
FROM   products
ORDER BY unit_price DESC
LIMIT 5;
```

**Practice:** List the 10 most recently signed-up customers (newest first) with their code and signup date.

<details><summary>Answer</summary>

```sql
SELECT customer_code, signup_date
FROM   customers
ORDER BY signup_date DESC
LIMIT 10;
```
</details>

---

## 4. GROUP BY - one row per group

**Idea:** `GROUP BY` puts rows with the same value into one bucket and returns **one row per bucket**.
You almost always combine it with an aggregate function (next sections use them together).

```sql
SELECT group_column, AGG(other_column)
FROM   table
GROUP BY group_column;
```

**Example** - how many customers per segment:
```sql
SELECT segment, COUNT(*) AS customers
FROM   customers
GROUP BY segment;
```

**Rule:** every column in SELECT must be either in GROUP BY or inside an aggregate.
`SELECT segment, city, COUNT(*) ... GROUP BY segment` is an error in MySQL 8 (which city should it show?).

**Practice:** Count products per category.

<details><summary>Answer</summary>

```sql
SELECT category, COUNT(*) AS products
FROM   products
GROUP BY category
ORDER BY products DESC;
```
</details>

---

## 5. HAVING - filter groups

**Idea:** `WHERE` filters rows **before** grouping. `HAVING` filters groups **after** grouping, so it can use aggregates.

```sql
SELECT col, COUNT(*) FROM t WHERE row_condition GROUP BY col HAVING COUNT(*) > 5;
```

**Example** - cities with at least 15 customers:
```sql
SELECT city, COUNT(*) AS customers
FROM   customers
GROUP BY city
HAVING COUNT(*) >= 15
ORDER BY customers DESC;
```

**Practice:** Which customers (by `customer_id`) have placed more than 20 orders, counting cancelled ones too?

<details><summary>Answer</summary>

```sql
SELECT customer_id, COUNT(*) AS orders
FROM   orders
GROUP BY customer_id
HAVING COUNT(*) > 20;
```
</details>

---

## 6. Aggregate functions

| Function | Returns |
|---|---|
| `COUNT(*)` | number of rows |
| `COUNT(col)` | number of non-NULL values |
| `COUNT(DISTINCT col)` | number of different values |
| `SUM(col)`, `AVG(col)` | total, average (NULLs ignored) |
| `MIN(col)`, `MAX(col)` | smallest, largest |

**Example** - payment KPIs per payment method:
```sql
SELECT payment_method,
       COUNT(*)              AS payments,
       SUM(amount)           AS total_amount,
       ROUND(AVG(amount), 2) AS avg_amount,
       MAX(amount)           AS largest
FROM   payments
WHERE  status = 'COMPLETED'
GROUP BY payment_method;
```

**Practice:** How many different customers placed an order in 2026, and what was the total value of their non-cancelled orders?

<details><summary>Answer</summary>

```sql
SELECT COUNT(DISTINCT customer_id) AS customers,
       SUM(order_total)            AS total_value
FROM   orders
WHERE  order_date >= '2026-01-01' AND order_date < '2027-01-01'
  AND  status <> 'CANCELLED';
```
(Using a date range instead of `YEAR(order_date) = 2026` lets MySQL use the index on `order_date`.)
</details>

---

## 7. JOINs - combine tables

**Idea:** data is split across tables (normalization), so you join them back using key columns.

| Join | Keeps |
|---|---|
| `INNER JOIN` (or just `JOIN`) | only rows that match in **both** tables |
| `LEFT JOIN` | **all** rows of the left table; NULLs where the right side has no match |
| `RIGHT JOIN` | mirror of LEFT (rarely used - swap the tables instead) |
| self join | a table joined to itself with two aliases |

```sql
SELECT a.col, b.col
FROM   table_a a
JOIN   table_b b ON b.a_id = a.id;
```

**Example (INNER)** - orders with customer names:
```sql
SELECT o.order_number, c.first_name, c.last_name, o.order_total
FROM   orders o
JOIN   customers c ON c.customer_id = o.customer_id
LIMIT 5;
```

**Example (LEFT)** - every product and how many lines it appears on (0 if never sold):
```sql
SELECT p.product_name, COUNT(oi.order_item_id) AS times_ordered
FROM   products p
LEFT JOIN order_items oi ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY times_ordered
LIMIT 5;
```
Note `COUNT(oi.order_item_id)` (not `COUNT(*)`): for an unsold product the joined columns are NULL, so it counts 0.

**Example (3 tables)** - which products did order ORD-100010 contain?
```sql
SELECT o.order_number, p.product_name, oi.quantity, oi.line_total
FROM   orders o
JOIN   order_items oi ON oi.order_id = o.order_id
JOIN   products p    ON p.product_id = oi.product_id
WHERE  o.order_number = 'ORD-100010';
```

**Practice:** List every employee with their department name.

<details><summary>Answer</summary>

```sql
SELECT e.first_name, e.last_name, e.job_title, d.department_name
FROM   employees e
JOIN   departments d ON d.department_id = e.department_id
ORDER BY d.department_name;
```
</details>

**Practice 2:** Find customers who have never placed an order.

<details><summary>Answer</summary>

```sql
SELECT c.customer_code, c.first_name, c.last_name
FROM   customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE  o.order_id IS NULL;
```
</details>

---

## 8. Subqueries - a query inside a query

**Idea:** a SELECT inside another statement. Three common places:

| Where | Returns | Example use |
|---|---|---|
| in `WHERE` | one value, or a list for `IN` | "above average", "in this list" |
| in `FROM` (derived table) | a temporary table; needs an alias | aggregate of an aggregate |
| `EXISTS (...)` | true/false | "has at least one ..." |

A **correlated** subquery refers to the outer query's row and runs once per outer row.

**Example** - orders larger than the average order:
```sql
SELECT order_number, order_total
FROM   orders
WHERE  order_total > (SELECT AVG(order_total) FROM orders)
ORDER BY order_total DESC
LIMIT 5;
```

**Example (EXISTS)** - customers who have at least one FAILED payment:
```sql
SELECT c.customer_code, c.first_name
FROM   customers c
WHERE  EXISTS (SELECT 1
               FROM   orders o
               JOIN   payments p ON p.order_id = o.order_id
               WHERE  o.customer_id = c.customer_id
                 AND  p.status = 'FAILED');
```

**Practice:** Show products whose price is higher than the average price of *all* products.

<details><summary>Answer</summary>

```sql
SELECT product_name, unit_price
FROM   products
WHERE  unit_price > (SELECT AVG(unit_price) FROM products);
```
</details>

---

## 9. CASE - if/else inside SQL

```sql
CASE
    WHEN condition1 THEN result1
    WHEN condition2 THEN result2
    ELSE default_result
END
```
Conditions are checked top to bottom; the first true one wins.

**Example** - label stock levels:
```sql
SELECT product_name, stock_quantity,
       CASE
           WHEN stock_quantity = 0   THEN 'Out of stock'
           WHEN stock_quantity < 50  THEN 'Low'
           ELSE 'OK'
       END AS stock_level
FROM   products
ORDER BY stock_quantity
LIMIT 10;
```

**CASE inside an aggregate = conditional aggregation** (count different things in one pass):
```sql
SELECT COUNT(*)                                              AS all_orders,
       SUM(CASE WHEN status = 'DELIVERED' THEN 1 ELSE 0 END) AS delivered,
       SUM(CASE WHEN status = 'CANCELLED' THEN 1 ELSE 0 END) AS cancelled
FROM   orders;
```

`COALESCE(a, b, ...)` returns the first value that is not NULL - a compact "if NULL then ...":
```sql
SELECT order_number, COALESCE(employee_id, 0) AS employee_or_zero FROM orders LIMIT 5;
```

**Practice:** For each customer segment, count how many customers signed up in 2024 and how many in 2025, as two columns.

<details><summary>Answer</summary>

```sql
SELECT segment,
       SUM(CASE WHEN YEAR(signup_date) = 2024 THEN 1 ELSE 0 END) AS signed_up_2024,
       SUM(CASE WHEN YEAR(signup_date) = 2025 THEN 1 ELSE 0 END) AS signed_up_2025
FROM   customers
GROUP BY segment;
```
</details>

---

## 10. CTE (Common Table Expression) - `WITH`

**Idea:** give a subquery a **name** at the top, then use it like a table. Makes multi-step logic readable.

```sql
WITH step1 AS (
    SELECT ...
),
step2 AS (
    SELECT ... FROM step1 ...
)
SELECT ... FROM step2;
```

**Example** - customers whose total spend is above ₹10 lakh:
```sql
WITH customer_totals AS (
    SELECT customer_id, SUM(order_total) AS total_spent
    FROM   orders
    WHERE  status <> 'CANCELLED'
    GROUP BY customer_id
)
SELECT c.customer_code, c.first_name, ct.total_spent
FROM   customer_totals ct
JOIN   customers c ON c.customer_id = ct.customer_id
WHERE  ct.total_spent > 1000000
ORDER BY ct.total_spent DESC;
```

**Recursive CTE** (for hierarchies) - see Q26 in `database/queries.sql` (the company org chart).

**Practice:** Using a CTE, compute revenue per category, then show only categories with revenue above ₹2 crore (20,000,000).

<details><summary>Answer</summary>

```sql
WITH category_revenue AS (
    SELECT p.category, SUM(oi.line_total) AS revenue
    FROM   order_items oi
    JOIN   products p ON p.product_id = oi.product_id
    JOIN   orders o   ON o.order_id = oi.order_id
    WHERE  o.status <> 'CANCELLED'
    GROUP BY p.category
)
SELECT category, revenue
FROM   category_revenue
WHERE  revenue > 20000000
ORDER BY revenue DESC;
```
</details>

---

## 11. Window functions - calculations across related rows *without* collapsing them

**Idea:** like an aggregate, but every row stays in the result and gets an extra computed column.

```sql
FUNCTION() OVER (PARTITION BY group_col ORDER BY sort_col)
```
- `PARTITION BY` = "restart for each group" (optional)
- `ORDER BY` = the order inside each group (needed for ranking, running totals, LAG)

| Function | Gives |
|---|---|
| `ROW_NUMBER()` | 1, 2, 3, ... (no ties) |
| `RANK()` / `DENSE_RANK()` | ranking with ties (1,2,2,4 / 1,2,2,3) |
| `SUM(x) OVER (ORDER BY ...)` | running total |
| `LAG(x)` / `LEAD(x)` | previous / next row's value |
| `NTILE(n)` | splits rows into n buckets |

**Example** - rank products by price inside each category:
```sql
SELECT category, product_name, unit_price,
       RANK() OVER (PARTITION BY category ORDER BY unit_price DESC) AS price_rank
FROM   products
ORDER BY category, price_rank;
```

**Example** - running total of revenue by month (uses a view from this project):
```sql
SELECT sales_month, revenue,
       SUM(revenue) OVER (ORDER BY sales_month) AS running_total
FROM   vw_monthly_sales;
```

**Practice:** For every order, show the customer's previous order date using `LAG`.

<details><summary>Answer</summary>

```sql
SELECT customer_id, order_number, order_date,
       LAG(order_date) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order_date
FROM   orders
ORDER BY customer_id, order_date
LIMIT 20;
```
</details>

**Practice 2:** Show each customer's single most expensive order (top-1 per group).

<details><summary>Answer</summary>

```sql
WITH ranked AS (
    SELECT customer_id, order_number, order_total,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_total DESC) AS rn
    FROM   orders
)
SELECT customer_id, order_number, order_total
FROM   ranked
WHERE  rn = 1;
```
(You can't write `WHERE ROW_NUMBER() ... = 1` directly: window functions are computed after WHERE.)
</details>

---

## 12. Views - saved queries

**Idea:** `CREATE VIEW name AS SELECT ...` saves a query under a name. You query it like a table.
It stores **no data** - it runs its SELECT every time.

```sql
CREATE OR REPLACE VIEW view_name AS
SELECT ...;
```

**Example** - this project's `vw_order_summary` joins 5 tables and calculates the payment status. Using it is easy:
```sql
SELECT order_number, customer_name, order_total, amount_paid, balance_due, payment_status
FROM   vw_order_summary
WHERE  payment_status = 'UNPAID'
LIMIT 10;
```

Why use views: reuse one definition (e.g. "revenue"), hide complex joins, restrict what users can see.

**Practice:** Using `vw_customer_360`, find the number of customers in each tier.

<details><summary>Answer</summary>

```sql
SELECT tier, COUNT(*) AS customers
FROM   vw_customer_360
GROUP BY tier;
```
</details>

---

## 13. Stored procedures (and functions)

**Idea:** a **procedure** is a named program stored in the database and run with `CALL`. It can take
`IN` parameters, return `OUT` parameters, return result sets, use variables, `IF`, and transactions.
A **function** returns a single value and can be used inside SELECT.

```sql
DELIMITER $$
CREATE PROCEDURE procedure_name(IN p_param INT)
BEGIN
    -- statements; each ends with ;
END$$
DELIMITER ;

CALL procedure_name(5);
```
`DELIMITER $$` tells the mysql client that the whole block ends at `$$`, because the body itself contains `;`.

**Examples from the project**
```sql
CALL sp_get_customer_summary(1);                        -- one-row summary of customer 1
CALL sp_sales_report('2026-01-01', '2026-04-01');       -- monthly report for Jan-Mar 2026
SELECT fn_order_balance(1), fn_customer_tier(1);        -- functions inside SELECT
```

Errors inside a procedure are raised with `SIGNAL`:
```sql
CALL sp_update_order_status(1, 'PENDING');
-- ERROR 1644 (45000): Invalid status transition   (order 1 is already DELIVERED)
```

**Practice:** Call the procedure that runs the in-database data-quality checks and show how many new issues it found.

<details><summary>Answer</summary>

```sql
CALL sp_run_data_quality_checks(@found);
SELECT @found;                -- 0 if nothing new since the last run
```
`@found` is a **session variable** that receives the OUT parameter.
</details>

---

## 14. Triggers

**Idea:** SQL that MySQL runs **automatically** when a row is inserted, updated or deleted. You never call it.

```sql
CREATE TRIGGER trigger_name
{BEFORE | AFTER} {INSERT | UPDATE | DELETE} ON table_name
FOR EACH ROW
BEGIN
    -- NEW.col = new value (INSERT, UPDATE); OLD.col = old value (UPDATE, DELETE)
END
```
- `BEFORE` triggers can change `NEW` values or reject the row (`SIGNAL`).
- `AFTER` triggers do side effects (write an audit row, update a total).

**Project examples:** `trg_customers_before_insert` (cleans email), `trg_order_items_after_insert`
(recomputes `orders.order_total`), `trg_customers_audit_update` (writes to `audit_logs`).

See them working (the transaction is rolled back, so nothing is saved):
```sql
START TRANSACTION;
UPDATE customers SET city = 'Nagpur' WHERE customer_id = 1;
SELECT action, old_values, new_values, changed_by
FROM   audit_logs
WHERE  table_name = 'customers' AND record_id = 1
ORDER BY audit_id DESC LIMIT 1;
ROLLBACK;
```

**Practice:** Show the 5 most recent UPDATE entries in the audit log for the `orders` table.

<details><summary>Answer</summary>

```sql
SELECT audit_id, record_id, old_values, new_values, changed_by, changed_at
FROM   audit_logs
WHERE  table_name = 'orders' AND action = 'UPDATE'
ORDER BY changed_at DESC, audit_id DESC
LIMIT 5;
```
</details>

---

## 15. Transactions

**Idea:** a group of statements that succeed or fail **together**.

```sql
START TRANSACTION;
  -- statement 1
  -- statement 2
COMMIT;      -- make all changes permanent
-- or
ROLLBACK;    -- undo all changes since START TRANSACTION
```

**ACID**: **A**tomic (all or nothing), **C**onsistent (constraints always hold), **I**solated
(concurrent transactions don't see each other's half-done work), **D**urable (after COMMIT it survives a crash).

**Example** - experiment safely, then undo:
```sql
START TRANSACTION;
UPDATE products SET unit_price = unit_price * 0.9 WHERE category = 'Printers';
SELECT product_name, unit_price FROM products WHERE category = 'Printers';
ROLLBACK;
SELECT product_name, unit_price FROM products WHERE category = 'Printers';   -- prices are back
```

In this project `sp_record_payment` locks the order with `SELECT ... FOR UPDATE`, validates, inserts and
`COMMIT`s - or `ROLLBACK`s on any error. Try an overpayment:
```sql
CALL sp_record_payment(1, 99999999, 'UPI', 'TEST-OVERPAY', @id);
-- ERROR 1644 (45000): Payment exceeds outstanding balance   -> nothing was saved
```

**Practice:** Inside a transaction, delete all `IGNORED` data-quality issues, check the count, then undo it.

<details><summary>Answer</summary>

```sql
START TRANSACTION;
DELETE FROM data_quality_issues WHERE resolution_status = 'IGNORED';
SELECT COUNT(*) FROM data_quality_issues WHERE resolution_status = 'IGNORED';   -- 0
ROLLBACK;
```
</details>

---

## 16. Indexes

**Idea:** a sorted structure (B+tree) on one or more columns so MySQL can find rows without reading the whole table -
like the index at the back of a book. Faster reads, slightly slower writes.

```sql
CREATE INDEX index_name ON table_name (col1, col2);
SHOW INDEX FROM table_name;
EXPLAIN SELECT ...;            -- shows whether an index is used
EXPLAIN ANALYZE SELECT ...;    -- runs it and shows real timings
```

**Example** - the project's `idx_orders_order_date` is used here:
```sql
EXPLAIN
SELECT order_number FROM orders
WHERE  order_date >= '2026-09-01' AND order_date < '2026-09-08';
-- -> Index range scan on orders using idx_orders_order_date
```
...but **not** here, because of the function around the column:
```sql
EXPLAIN
SELECT order_number FROM orders
WHERE  DATE(order_date) = '2026-09-01';
-- -> Table scan on orders
```

Composite index `(customer_id, order_date)` → works for `WHERE customer_id = ?` and
`WHERE customer_id = ? ORDER BY order_date`, **not** for `WHERE order_date = ?` alone (leftmost-prefix rule).

**Practice:** Check which index MySQL uses to find all payments of order 500.

<details><summary>Answer</summary>

```sql
EXPLAIN SELECT * FROM payments WHERE order_id = 500;
-- uses idx_payments_order_status (its first column is order_id)
```
</details>

---

### Where to go next
- Read `database/queries.sql` top to bottom (32 queries, same order as this guide).
- `docs/SQL_EXPLANATION.md` explains each query, plus procedures, triggers, and EXPLAIN plans.
