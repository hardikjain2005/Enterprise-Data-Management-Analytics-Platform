# SQL Explanation

This file explains every SQL object in `database/`. Query numbers (Q1...) match `database/queries.sql`.
Results quoted below are from the demo data loaded by `./etl/scripts/load_demo_data.sh`.

Business rule used everywhere: **revenue = `order_total` of orders that are not `CANCELLED`**.

---

## Part A - Basics

### Q1. Corporate customers from Maharashtra, newest first
```sql
SELECT customer_code, first_name, last_name, city, signup_date
FROM   customers
WHERE  segment = 'Corporate' AND state = 'Maharashtra'
ORDER BY signup_date DESC;
```
- **What:** filters rows with two conditions and sorts them.
- **Why useful:** typical "list for the sales team" request.
- **Syntax:** `WHERE` keeps rows where the condition is true; `AND` = both must be true; `ORDER BY ... DESC` = largest/newest first.
- **Interviewer may ask:** *In what order does SQL run the clauses?* → `FROM` → `WHERE` → `GROUP BY` → `HAVING` → `SELECT` → `ORDER BY` → `LIMIT`.

### Q2. Distinct customer cities
- **What:** `SELECT DISTINCT city, country` returns each city/country pair once (17 rows).
- **Why:** shows market coverage; also used to fill drop-downs.
- **Syntax:** `DISTINCT` removes duplicate *rows* of the selected columns (not just one column).
- **Ask:** *DISTINCT vs GROUP BY?* → same result here; GROUP BY is needed when you also want aggregates per group.

### Q3. Overall sales KPIs
- **What:** `COUNT(*)`, `SUM`, `AVG`, `MIN`, `MAX` over non-cancelled orders → 1,424 orders, ₹23.86 Cr revenue.
- **Why:** the numbers on the dashboard.
- **Syntax:** aggregate functions collapse many rows into one. `ROUND(x, 2)` rounds to 2 decimals.
- **Ask:** *COUNT(\*) vs COUNT(column)?* → `COUNT(*)` counts rows; `COUNT(col)` skips NULLs.
  *Smallest order is ₹0 - why?* → two orders whose only line was rejected by the ETL (they are flagged by the data-quality check `order_has_items`).

### Q4. Orders and value per status (GROUP BY)
- **What:** one row per status with its count and total value.
- **Syntax:** `GROUP BY status` puts rows with the same status in one bucket; aggregates are computed per bucket.
- **Ask:** *Can you SELECT a column that is not in GROUP BY?* → No (MySQL's `ONLY_FULL_GROUP_BY` mode rejects it) unless it is inside an aggregate.

### Q5. Customers with more than 15 orders (GROUP BY + HAVING)
```sql
SELECT customer_id, COUNT(*) AS order_count
FROM   orders
WHERE  status <> 'CANCELLED'
GROUP BY customer_id
HAVING COUNT(*) > 15
ORDER BY order_count DESC;
```
- **Why:** identifies loyal / key accounts.
- **Syntax:** `WHERE` filters *rows before* grouping; `HAVING` filters *groups after* grouping (can use aggregates).
- **Ask:** *Why not `WHERE COUNT(*) > 15`?* → aggregates don't exist yet when WHERE runs.

### Q6. Revenue per year and quarter
- **What:** `YEAR(order_date)`, `QUARTER(order_date)` grouped → revenue trend by quarter.
- **Why:** management reporting is done by quarter.
- **Ask:** *Does `WHERE YEAR(order_date) = 2026` use an index?* → No - wrapping the column in a function blocks the index. Use `order_date >= '2026-01-01' AND order_date < '2027-01-01'` (see Indexing, example 2).

### Q7. Orders per weekday
- **What:** `DAYNAME()` for the label, `DAYOFWEEK()` (1 = Sunday) for correct ordering.
- **Why:** staffing / campaign timing.
- **Ask:** *Why group by both?* → to sort Sunday→Saturday instead of alphabetically.

---

## Part B - Joins

### Q8. INNER JOIN - latest orders with customer names
```sql
SELECT o.order_number, o.order_date, CONCAT(c.first_name, ' ', c.last_name) AS customer_name, o.status, o.order_total
FROM   orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
ORDER BY o.order_date DESC
LIMIT 10;
```
- **What:** combines each order with its customer row.
- **Syntax:** `o`, `c` are table aliases; `ON` gives the matching condition; `LIMIT 10` returns the first 10.
- **Ask:** *What happens to an order with no matching customer?* → INNER JOIN drops it (impossible here because of the FK).

### Q9. LEFT JOIN - customers who never ordered
```sql
SELECT c.customer_code, CONCAT(c.first_name, ' ', c.last_name) AS customer_name, c.signup_date
FROM   customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE  o.order_id IS NULL;
```
- **What:** keeps **all** customers; where no order matches, the order columns are NULL → filter those. 19 customers.
- **Why:** re-activation campaign list.
- **Ask:** *Other ways?* → `NOT EXISTS (SELECT 1 FROM orders WHERE customer_id = c.customer_id)` (Q13 style) or `NOT IN` (careful: `NOT IN` breaks if the subquery returns a NULL).

### Q10. Four-table JOIN - lines of one order
- **What:** `orders → customers`, `orders → order_items → products`.
- **Why:** an invoice view.
- **Ask:** *How does MySQL execute this?* → nested-loop join, looking up each related row by primary/unique key (see EXPLAIN example 5).

### Q11. SELF JOIN - employee and manager
```sql
SELECT CONCAT(e.first_name,' ',e.last_name) AS employee, e.job_title, d.department_name,
       COALESCE(CONCAT(m.first_name,' ',m.last_name), '(top level)') AS manager
FROM   employees e
JOIN   departments d ON d.department_id = e.department_id
LEFT JOIN employees m ON m.employee_id = e.manager_id;
```
- **What:** the same table used twice with different aliases (`e` = employee, `m` = manager).
- **Why LEFT JOIN:** department heads have `manager_id = NULL` and must still appear.

### Q12. Revenue per sales employee
- **What:** LEFT JOIN orders with `AND o.status <> 'CANCELLED'` **inside the ON clause**.
- **Ask:** *Why put the condition in ON, not WHERE?* → In WHERE it would remove employees with no orders (NULL ≠ 'CANCELLED' is not TRUE), turning the LEFT JOIN into an INNER JOIN. The Head of Sales correctly shows 0 orders.

### Q13. Products never sold (NOT EXISTS)
- **What:** `WHERE NOT EXISTS (SELECT 1 FROM order_items oi WHERE oi.product_id = p.product_id)`.
- **Why:** dead stock. (Returns 0 rows in the demo - every product has sold.)
- **Ask:** *Why `SELECT 1`?* → EXISTS only checks whether a row exists; the selected value doesn't matter.

---

## Part C - Subqueries, CASE, COALESCE, conditional aggregation

### Q14. Correlated subquery - priced above category average
```sql
SELECT p.sku, p.product_name, p.category, p.unit_price
FROM   products p
WHERE  p.unit_price > (SELECT AVG(p2.unit_price) FROM products p2 WHERE p2.category = p.category);
```
- **What:** for every product, the inner query computes *its own category's* average.
- **Syntax:** "correlated" = the subquery refers to the outer row (`p.category`), so it is evaluated per outer row.
- **Ask:** *Rewrite without a correlated subquery?* → CTE/derived table with `GROUP BY category`, then JOIN; or `AVG(unit_price) OVER (PARTITION BY category)`.

### Q15. Subquery with IN - corporate customers who bought laptops
- **What:** inner query returns a list of `customer_id`s; outer query keeps customers in that list.
- **Ask:** *IN vs EXISTS?* → same result for non-NULL keys; EXISTS can stop at the first match; the MySQL optimizer often converts both into a semi-join.

### Q16. Derived table - average lines per order
```sql
SELECT ROUND(AVG(line_count), 2) AS avg_lines_per_order, MAX(line_count) AS max_lines_in_an_order
FROM  (SELECT order_id, COUNT(*) AS line_count FROM order_items GROUP BY order_id) AS per_order;
```
- **What:** aggregate of an aggregate (1.88 lines per order). A subquery in `FROM` must have an alias.

### Q17. CASE - order value bands
- **What:** `CASE WHEN ... THEN ... ELSE ... END` maps each order total to a band; then `GROUP BY` the band.
- **Insight:** 107 "very large" orders (≥ ₹5 L) bring ~47% of revenue.
- **Ask:** *Why the "1." prefixes?* → so `ORDER BY value_band` sorts bands logically.

### Q18. COALESCE - online vs sales-rep orders
- **What:** `COALESCE(a, b)` returns the first non-NULL value → `'Online (self-service)'` when there is no employee.

### Q19. Conditional aggregation (pivot)
```sql
SUM(CASE WHEN status = 'DELIVERED' THEN 1 ELSE 0 END) AS delivered,
...
ROUND(100 * SUM(status = 'CANCELLED') / COUNT(*), 1) AS cancel_rate_pct
```
- **What:** turns status *rows* into status *columns*, one row per month.
- **Syntax trick:** in MySQL a comparison returns 1 or 0, so `SUM(status = 'CANCELLED')` counts cancellations.
- **Why:** classic report layout; avoids running 5 separate queries.

---

## Part D - CTEs and window functions

### Q20. CTE - customers spending 2× their segment average
```sql
WITH customer_spend AS (...),     -- step 1: spend per customer
     segment_avg   AS (...)       -- step 2: average per segment, built FROM step 1
SELECT ... FROM customer_spend cs JOIN segment_avg sa ON sa.segment = cs.segment
WHERE cs.total_spent > 2 * sa.avg_spent;
```
- **What:** a CTE (`WITH name AS (...)`) is a named temporary result used by the next query. Here the second CTE reads the first.
- **Why:** step-by-step logic is readable and testable.
- **Ask:** *Subquery vs CTE?* → same power for this case; CTEs are readable, can be referenced several times, and can be **recursive** (Q26).

### Q21. ROW_NUMBER - latest order per customer
```sql
ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date DESC) AS rn
... WHERE r.rn = 1
```
- **What:** numbers each customer's orders 1, 2, 3... newest first; `rn = 1` is the latest.
- **Syntax:** `PARTITION BY` = restart numbering per customer; unlike GROUP BY, rows are **not collapsed**.
- **Ask:** *Why not filter `rn = 1` in the same query?* → window functions are computed after WHERE, so you wrap them in a CTE/subquery.
  This "top-N per group" pattern is also used in the view `vw_etl_job_status` (latest run per job).

### Q22. DENSE_RANK - top 3 products per category
- **Ask:** *ROW_NUMBER vs RANK vs DENSE_RANK?* For values 100, 90, 90, 80:
  ROW_NUMBER → 1,2,3,4 · RANK → 1,2,2,4 · DENSE_RANK → 1,2,2,3.

### Q23. Running total
```sql
SUM(revenue) OVER (ORDER BY sales_month) AS cumulative_revenue
```
- **What:** for each month, the sum of all months up to it (reaches ₹23.86 Cr). Shown on the Analytics page.

### Q24. LAG - month-over-month growth
```sql
ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY sales_month)) / LAG(revenue) OVER (ORDER BY sales_month), 1)
```
- **What:** `LAG(x)` = value of x in the previous row (NULL for the first month). `LEAD` looks forward.
- **Note:** Oct 2026 shows −81% because the data stops on 10 Oct - a partial month. Good to mention unprompted: it shows you read results critically.

### Q25. NTILE - spending quartiles
- **What:** `NTILE(4)` splits ordered customers into 4 equal groups; then aggregate per quartile.
- **Insight:** the top quartile (47 customers) spends ≥ ₹10.9 L each.

### Q26. Recursive CTE - org chart
- **What:** anchor = top managers (`manager_id IS NULL`); recursive part joins employees to the rows found so far; stops when no new rows. Builds `Rajesh Kulkarni > Priya Nair > Rohit Verma`.
- **Ask:** *What prevents an infinite loop?* → recursion ends when the recursive SELECT returns no rows; MySQL also caps depth with `cte_max_recursion_depth` (default 1000).

---

## Part E - Data quality & ETL monitoring

### Q27. Possible duplicate customers
- **What:** `GROUP BY first_name, last_name, city HAVING COUNT(*) > 1` → finds *Ira Mukherjee, Bengaluru* twice (`CUST-1021`, `CUST-1151`) with different emails. `GROUP_CONCAT` lists their codes in one cell.
- **Why:** this "soft duplicate" passes every row rule (different email, different code), so only a query like this catches it - a real-world data-stewardship task.

### Q28. Reconciliation - order total vs its lines
- **What:** returns orders where `order_total <> SUM(line_total)`. **Returns 0 rows**, which proves the triggers work. (Also an automated test.)

### Q29. ETL success rate per job
- **What:** `SUM(l.status = 'FAILED')` style counting, reject rate %, `NULLIF(x, 0)` to avoid division by zero, `TIMESTAMPDIFF` for duration.
- **Result:** `load_customers` has 3 runs: 1 success, 1 partial, 1 failed; 10.3% of its rows were rejected.

### Q30. Open issues by severity
- **What:** `ORDER BY FIELD(severity, 'CRITICAL','HIGH','MEDIUM','LOW')` - custom sort order (MySQL-specific function).

### Q31. Billed vs collected per month
- **What:** pre-aggregates payments per order in a derived table, LEFT JOINs to orders, computes outstanding and collection rate.
- **Ask:** *Why pre-aggregate payments first?* → joining orders directly to payments would repeat the order total once per payment (an order with 2 payments would be counted twice) - the classic "fan-out" mistake.
- **Insight:** a negative "outstanding" in some months is the overpayments (double charges) flagged by `no_overpayment`.

### Q32. Views + functions together
- `vw_customer_360` gives the list; `fn_customer_total_spent(customer_id)` returns the same number → the function and view agree (also an automated test).

---

## Views (`database/views.sql`)

A **view** is a saved SELECT that you query like a table. It stores no data (it runs its query each time).

| View | What it gives | Used by |
|---|---|---|
| `vw_order_summary` | order + customer + employee + item count + paid + balance + payment status (CASE) | Orders page, dashboard outstanding balance |
| `vw_customer_360` | customer + lifetime orders, spend, last order, days since last order, tier | Customers page, customer analytics |
| `vw_monthly_sales` | revenue, orders, unique customers, AOV per month | Analytics, Q23/Q24 |
| `vw_product_performance` | units, revenue per product + `RANK()` within category | Products page |
| `vw_etl_job_status` | each job + its latest run (CTE + ROW_NUMBER) + run counts | ETL Monitoring page |
| `vw_data_quality_summary` | issue counts per table / type / severity | ad-hoc reporting |

**Why views?** One definition of "revenue" or "payment status" shared by API, dashboard and analysts; hides joins;
can grant access to a view without exposing base tables.
The backend maps three views to **read-only SQLAlchemy models** (`backend/app/models/views.py`).

---

## Stored functions (`database/procedures.sql`)

A **function** returns one value and can be used inside a SELECT.

| Function | Returns | Runs when |
|---|---|---|
| `fn_customer_total_spent(customer_id)` | lifetime value of non-cancelled orders | whenever a query calls it |
| `fn_order_balance(order_id)` | `order_total − completed payments` (NULL if order not found) | used by `sp_record_payment` and the API after a payment |
| `fn_customer_tier(customer_id)` | `PLATINUM` ≥ ₹10 L, `GOLD` ≥ ₹4 L, `SILVER` ≥ ₹1 L, else `BRONZE` | used by `vw_customer_360` and `sp_get_customer_summary` |

`fn_customer_tier` calls `fn_customer_total_spent`, so "what counts as spend" is defined once.
Functions are declared `READS SQL DATA` because MySQL's binary logging requires a function to say whether it changes data.

## Stored procedures

A **procedure** is a saved program you run with `CALL`. It can have IN/OUT parameters, return result sets, use IF/variables and control transactions.

| Procedure | When it runs | What it does | Why it is useful |
|---|---|---|---|
| `sp_get_customer_summary(id)` | `GET /api/customers/{id}` | one row: orders, cancelled, spent, paid, first/last order, tier | one reusable "customer order totals" calculation |
| `sp_update_order_status(id, status)` | `PATCH /api/orders/{id}/status` | allows only PENDING→PROCESSING→SHIPPED→DELIVERED and PENDING/PROCESSING→CANCELLED; otherwise `SIGNAL SQLSTATE '45000'` | business rule enforced in the DB for every client; the audit trigger records the change |
| `sp_record_payment(order, amount, method, ref, OUT id)` | `POST /api/payments` | **transaction**: lock order row (`SELECT ... FOR UPDATE`), check order exists / not cancelled / amount > 0 / not more than balance, insert, `COMMIT`; any error → `ROLLBACK` + re-raise | shows atomicity and concurrency control |
| `sp_sales_report(start, end)` | ad hoc / reporting | monthly orders, cancellations, customers, revenue, AOV for a half-open date range | operational report with input validation |
| `sp_run_data_quality_checks(OUT n)` | after every ETL run and from the Data Quality page | 5 cross-table rules → `data_quality_issues`; skips problems already OPEN so it never duplicates | data validation that needs several tables |

The 5 in-database checks: order has items · delivered order fully paid · no overpayment · payment not before order · order not before customer signup.
Results in the demo: 25 delivered-but-unpaid, 4 overpaid (2 double charges + 2 orders whose only item was rejected), 2 orders with no items, 2 payments before order, 2 orders before signup.

**Key syntax inside `sp_record_payment`:**
```sql
DECLARE EXIT HANDLER FOR SQLEXCEPTION
BEGIN
    ROLLBACK;     -- undo everything done since START TRANSACTION
    RESIGNAL;     -- pass the original error to the caller
END;
START TRANSACTION;
SELECT status INTO v_status FROM orders WHERE order_id = p_order_id FOR UPDATE;   -- row lock
...
IF p_amount > v_balance THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Payment exceeds outstanding balance';
END IF;
INSERT INTO payments (...) VALUES (...);
COMMIT;
```
`SIGNAL` raises a custom error (like `throw`); the handler catches it, rolls back, and re-raises; the API turns it into HTTP 400.

**DELIMITER:** routines contain `;`, so the script switches the mysql client's terminator to `$$` while defining them.

> These are MySQL *stored programs*. (PL/SQL is Oracle's language; this project does not use it.)

---

## Triggers (`database/triggers.sql`) - 19 in total

A **trigger** runs automatically on INSERT/UPDATE/DELETE of a table. `NEW` = the new row values, `OLD` = the previous ones.

| Trigger(s) | Fires | Does | Why |
|---|---|---|---|
| `trg_customers_before_insert` / `_before_update` | BEFORE INSERT/UPDATE on customers | trims names, lower-cases email; rejects a future `signup_date` with SIGNAL | data validation for *every* writer, not only the ETL |
| `trg_order_items_after_insert` / `_update` / `_delete` | AFTER each change to order lines | recalculates `orders.order_total = SUM(line_total)` | maintains a derived value automatically |
| `trg_customers_audit_*`, `trg_products_audit_*`, `trg_orders_audit_*`, `trg_payments_audit_*` (12) | AFTER INSERT/UPDATE/DELETE | writes table, record id, action, old/new values (JSON), `changed_by`, time to `audit_logs` | full change history |
| `trg_audit_logs_no_update` / `_no_delete` | BEFORE UPDATE/DELETE on audit_logs | always `SIGNAL` an error | audit trail must be tamper-proof (append-only) |

Details worth knowing:
- **Who changed it?** Programs run `SET @app_user = 'etl_pipeline'` (or `'api'`) on their connection; the trigger stores `COALESCE(@app_user, USER())`.
- **No-op updates are not logged:** UPDATE triggers compare `OLD.col <=> NEW.col` (`<=>` is NULL-safe equality). The orders trigger also ignores `order_total`, which is derived.
- **Audit is transactional:** if the change is rolled back, its audit row is rolled back too (verified).
- **Cascade gotcha:** rows deleted by `ON DELETE CASCADE` do **not** fire triggers in MySQL.
- **Error 1442:** a trigger can't modify a table the triggering statement reads - this shaped the ETL design (see ARCHITECTURE.md).

---

## Transactions in this project

| Where | What is atomic |
|---|---|
| `sp_record_payment` | lock + validate + insert payment (explicit `START TRANSACTION ... COMMIT/ROLLBACK`) |
| ETL `load` step (`engine.begin()`) | issues + staging + reference checks + upsert + execution-log update for one job |
| API services | `db.commit()` / `db.rollback()` around procedure calls |
| Tests | most DB tests run inside a transaction that is rolled back, so they leave no data behind |

---

## Indexing and query optimization

### What an index is
A sorted lookup structure (a **B+tree** in InnoDB) on one or more columns, like a book index:
instead of reading every page (full table scan), MySQL jumps to the matching entries.
In InnoDB the **primary key is the clustered index** - the table rows themselves are stored in PK order;
secondary indexes store the indexed columns + the primary key.

### Indexes in this project (`database/indexes.sql`) and the query each one serves

| Index | Columns | Serves |
|---|---|---|
| `idx_orders_order_date` | `order_date` | date-range filters, monthly reports |
| `idx_orders_customer_date` | `customer_id, order_date` | "orders of customer X newest first" (also serves the customer FK) |
| `idx_orders_status_date` | `status, order_date` | status filter within a period (status alone has only 5 values) |
| `idx_payments_order_status` | `order_id, status` | paid amount per order (covering for counts) |
| `idx_payments_payment_date` | `payment_date` | Payments page date filter |
| `idx_order_items_product` | `product_id` | product performance |
| `idx_products_category`, `idx_customers_segment`, `idx_customers_signup_date` | | page filters, new customers per month |
| `idx_etl_logs_job_started`, `idx_etl_logs_status` | | latest run per job, failed-run count |
| `idx_dq_status_severity`, `idx_dq_table_type` | | Data Quality filters / summaries |
| `idx_audit_table_record`, `idx_audit_changed_at` | | history of one record, recent changes |

PKs and UNIQUE constraints already create indexes, so they are not repeated.
**Composite index rule (leftmost prefix):** `(customer_id, order_date)` helps `WHERE customer_id = ?` and
`WHERE customer_id = ? AND order_date > ?`, but **not** `WHERE order_date > ?` alone. Put equality columns first, range/sort column last.

### EXPLAIN results (real output, MySQL 9.6, `database/explain_examples.sql`)

**1. Range filter on an indexed column → index used**
```
-> Index range scan on orders using idx_orders_order_date
   over ('2026-09-01 00:00:00' <= order_date < '2026-09-08 00:00:00')
```

**2. Same filter with a function on the column → full scan**
```sql
WHERE DATE(order_date) BETWEEN '2026-09-01' AND '2026-09-07'
```
```
-> Filter: (cast(orders.order_date as date) between '2026-09-01' and '2026-09-07')  (cost=155 rows=1525)
    -> Table scan on orders  (cost=155 rows=1525)
```
Lesson: keep indexed columns "bare" in WHERE.

**3. Composite index vs no index (EXPLAIN ANALYZE, customer 30)**
With `idx_orders_customer_date`:
```
-> Index lookup on orders using idx_orders_customer_date (customer_id = 30) (reverse)
   (cost=10.6 rows=38) (actual time=0.052..0.078 rows=38 loops=1)
```
After `ALTER TABLE orders ALTER INDEX idx_orders_customer_date INVISIBLE`:
```
-> Sort: orders.order_date DESC  (cost=152 rows=1495) (actual time=0.327..0.329 rows=38 loops=1)
    -> Filter: (orders.customer_id = 30)
        -> Table scan on orders  (actual ... rows=1525 loops=1)
```
Reads 1,525 rows instead of 38, adds a sort, ~4× slower even on this tiny table (it grows with the table).
The index is read **in reverse** to satisfy `ORDER BY order_date DESC` - no sort needed.
Discovery: when the composite index was created, MySQL **silently dropped the index it had auto-created for the
`customer_id` foreign key**, because the new index starts with `customer_id` and can serve the FK.
(`SHOW INDEX FROM orders` has no separate `fk_orders_customer` index.)

**4. Covering index**
```
-> Covering index lookup on payments using idx_payments_order_status (order_id = 500, status = 'COMPLETED')
```
Every column the query needs is inside the index, so the table rows are never read.

**5. Join**
```
-> Nested loop inner join
    -> Index range scan on o using idx_orders_order_date ...
    -> Single-row index lookup on c using PRIMARY (customer_id = o.customer_id)
```

### When indexes hurt
- Every INSERT/UPDATE/DELETE must also update every index → slower writes (that's why staging tables have none).
- They use disk and memory.
- Low-selectivity columns (`is_active` with 2 values) are rarely chosen by the optimizer → not indexed here.
- Too many overlapping indexes confuse maintenance; MySQL 8 **invisible indexes** let you test removing one safely.

### How to find and fix an expensive query
1. Find it: slow query log (`long_query_time`), `performance_schema` / `sys.statements_with_full_table_scans`, or API timing.
2. `EXPLAIN` → look for `Table scan`/`type=ALL`, large `rows`, `Using filesort`, `Using temporary`.
3. `EXPLAIN ANALYZE` → real time and rows per step.
4. Fix: add/adjust an index for the WHERE/JOIN/ORDER BY columns, remove functions on indexed columns,
   select only needed columns, pre-aggregate before joining (Q31), paginate with LIMIT, avoid N+1 queries.
5. Re-measure.

### Other optimizations already used
- Half-open date ranges (`>= start AND < end`) in the API, `sp_sales_report` and the views.
- Pagination (`LIMIT/OFFSET`) on every list endpoint.
- Dashboard KPIs fetched with **one** query of scalar subqueries instead of 10 round trips.
- Payments pre-aggregated in a derived table before joining (`vw_order_summary`, Q31) - avoids fan-out.
- `order_total` stored instead of re-summing lines in every report.
