"""
LOAD step: staging tables -> SQL reference checks -> production tables.

For every dataset the same 4 SQL steps run inside ONE transaction:

  1. RESOLVE  business keys to surrogate ids in staging
              (UPDATE stg_orders JOIN customers ... SET stg_orders.customer_id = ...)
  2. CHECK    rows whose reference could not be resolved -> data_quality_issues,
              and mark them load_status = 'REJECTED'
  3. UPSERT   the remaining rows into production:
              INSERT ... SELECT ... ON DUPLICATE KEY UPDATE
              (new key -> INSERT, existing key -> UPDATE; re-running is safe)
  4. MARK     loaded rows load_status = 'LOADED'

Why resolve ids in staging first? A MySQL trigger cannot update a table that
the triggering statement is reading (error 1442). The order_items trigger
updates `orders`, so the INSERT into order_items must read ONLY from staging.
"""

import pandas as pd
from sqlalchemy import text

# ---------------------------------------------------------------------
# Per-dataset SQL. Every statement uses :eid = the current execution_id.
# ---------------------------------------------------------------------
LOAD_PLANS = {
    "customers": {
        "staging": "stg_customers",
        "target": "customers",
        "target_pk": "customer_id",
        "match_existing": "t.customer_code = s.customer_code",
        "resolve": [],
        "checks": [
            {   # Email already belongs to a DIFFERENT customer in production
                "rule": "unique_email_db", "column": "email", "issue_type": "DUPLICATE_RECORD",
                "severity": "HIGH",
                "join": "JOIN customers c ON c.email = s.email AND c.customer_code <> s.customer_code",
                "condition": "TRUE",
                "description": "CONCAT('Row ', s.source_row, ': email ', s.email, "
                               "' already belongs to existing customer ', c.customer_code)",
                "identifier": "s.customer_code",
            },
        ],
        "upsert": """
            INSERT INTO customers (customer_code, first_name, last_name, email, phone,
                                   city, state, country, segment, signup_date)
            SELECT s.customer_code, s.first_name, s.last_name, s.email, s.phone,
                   s.city, s.state, s.country, s.segment, s.signup_date
              FROM stg_customers s
             WHERE s.execution_id = :eid AND s.load_status = 'PENDING'
            ON DUPLICATE KEY UPDATE
                first_name = s.first_name, last_name = s.last_name, email = s.email,
                phone = s.phone, city = s.city, state = s.state, country = s.country,
                segment = s.segment
        """,
    },
    "products": {
        "staging": "stg_products",
        "target": "products",
        "target_pk": "product_id",
        "match_existing": "t.sku = s.sku",
        "resolve": [],
        "checks": [],
        "upsert": """
            INSERT INTO products (sku, product_name, category, unit_price, stock_quantity)
            SELECT s.sku, s.product_name, s.category, s.unit_price, s.stock_quantity
              FROM stg_products s
             WHERE s.execution_id = :eid AND s.load_status = 'PENDING'
            ON DUPLICATE KEY UPDATE
                product_name = s.product_name, category = s.category,
                unit_price = s.unit_price, stock_quantity = s.stock_quantity
        """,
    },
    "orders": {
        "staging": "stg_orders",
        "target": "orders",
        "target_pk": "order_id",
        "match_existing": "t.order_number = s.order_number",
        "resolve": [
            """UPDATE stg_orders s
                 JOIN customers c ON c.customer_code = s.customer_code
                  SET s.customer_id = c.customer_id
                WHERE s.execution_id = :eid""",
            """UPDATE stg_orders s
                 JOIN employees e ON e.employee_code = s.employee_code
                  SET s.employee_id = e.employee_id
                WHERE s.execution_id = :eid""",
        ],
        "checks": [
            {
                "rule": "customer_exists", "column": "customer_code", "issue_type": "INVALID_REFERENCE",
                "severity": "HIGH", "join": "", "condition": "s.customer_id IS NULL",
                "description": "CONCAT('Row ', s.source_row, ': customer ', s.customer_code, ' does not exist')",
                "identifier": "s.order_number",
            },
            {
                "rule": "employee_exists", "column": "employee_code", "issue_type": "INVALID_REFERENCE",
                "severity": "MEDIUM", "join": "",
                "condition": "s.employee_code IS NOT NULL AND s.employee_id IS NULL",
                "description": "CONCAT('Row ', s.source_row, ': employee ', s.employee_code, ' does not exist')",
                "identifier": "s.order_number",
            },
        ],
        "upsert": """
            INSERT INTO orders (order_number, customer_id, employee_id, order_date, status)
            SELECT s.order_number, s.customer_id, s.employee_id, s.order_date, s.status
              FROM stg_orders s
             WHERE s.execution_id = :eid AND s.load_status = 'PENDING'
            ON DUPLICATE KEY UPDATE
                customer_id = s.customer_id, employee_id = s.employee_id,
                order_date = s.order_date, status = s.status
        """,
    },
    "order_items": {
        "staging": "stg_order_items",
        "target": "order_items",
        "target_pk": "order_item_id",
        "match_existing": "t.order_id = s.order_id AND t.product_id = s.product_id",
        "resolve": [
            """UPDATE stg_order_items s
                 JOIN orders o ON o.order_number = s.order_number
                  SET s.order_id = o.order_id
                WHERE s.execution_id = :eid""",
            """UPDATE stg_order_items s
                 JOIN products p ON p.sku = s.sku
                  SET s.product_id = p.product_id
                WHERE s.execution_id = :eid""",
        ],
        "checks": [
            {
                "rule": "order_exists", "column": "order_number", "issue_type": "INVALID_REFERENCE",
                "severity": "HIGH", "join": "", "condition": "s.order_id IS NULL",
                "description": "CONCAT('Row ', s.source_row, ': order ', s.order_number, "
                               "' does not exist (missing or rejected earlier)')",
                "identifier": "CONCAT(s.order_number, '|', s.sku)",
            },
            {
                "rule": "product_exists", "column": "sku", "issue_type": "INVALID_REFERENCE",
                "severity": "HIGH", "join": "", "condition": "s.product_id IS NULL",
                "description": "CONCAT('Row ', s.source_row, ': product ', s.sku, ' does not exist')",
                "identifier": "CONCAT(s.order_number, '|', s.sku)",
            },
        ],
        "upsert": """
            INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct)
            SELECT s.order_id, s.product_id, s.quantity, s.unit_price, s.discount_pct
              FROM stg_order_items s
             WHERE s.execution_id = :eid AND s.load_status = 'PENDING'
            ON DUPLICATE KEY UPDATE
                quantity = s.quantity, unit_price = s.unit_price, discount_pct = s.discount_pct
        """,
    },
    "payments": {
        "staging": "stg_payments",
        "target": "payments",
        "target_pk": "payment_id",
        "match_existing": "t.payment_reference = s.payment_reference",
        "resolve": [
            """UPDATE stg_payments s
                 JOIN orders o ON o.order_number = s.order_number
                  SET s.order_id = o.order_id
                WHERE s.execution_id = :eid""",
        ],
        "checks": [
            {
                "rule": "order_exists", "column": "order_number", "issue_type": "INVALID_REFERENCE",
                "severity": "HIGH", "join": "", "condition": "s.order_id IS NULL",
                "description": "CONCAT('Row ', s.source_row, ': order ', s.order_number, "
                               "' does not exist (missing or rejected earlier)')",
                "identifier": "s.payment_reference",
            },
            {   # Same transaction id already stored for a DIFFERENT order = conflicting duplicate
                "rule": "unique_reference_db", "column": "payment_reference", "issue_type": "DUPLICATE_RECORD",
                "severity": "CRITICAL",
                "join": "JOIN payments p ON p.payment_reference = s.payment_reference AND p.order_id <> s.order_id",
                "condition": "TRUE",
                "description": "CONCAT('Row ', s.source_row, ': transaction ', s.payment_reference, "
                               "' is already recorded for another order')",
                "identifier": "s.payment_reference",
            },
        ],
        "upsert": """
            INSERT INTO payments (payment_reference, order_id, payment_date, amount, payment_method, status)
            SELECT s.payment_reference, s.order_id, s.payment_date, s.amount, s.payment_method, s.status
              FROM stg_payments s
             WHERE s.execution_id = :eid AND s.load_status = 'PENDING'
            ON DUPLICATE KEY UPDATE
                payment_date = s.payment_date, amount = s.amount,
                payment_method = s.payment_method, status = s.status
        """,
    },
}


# ---------------------------------------------------------------------
# ETL execution log helpers
# ---------------------------------------------------------------------
def start_execution(conn, job_id: int) -> int:
    result = conn.execute(
        text("INSERT INTO etl_execution_logs (job_id, started_at, status) VALUES (:job, NOW(3), 'RUNNING')"),
        {"job": job_id},
    )
    return result.lastrowid


def finish_execution(conn, execution_id: int, stats: dict, status: str, error: str | None = None):
    conn.execute(
        text("""
            UPDATE etl_execution_logs
               SET ended_at = NOW(3), records_read = :read, records_inserted = :inserted,
                   records_updated = :updated, records_rejected = :rejected,
                   error_count = :errors, status = :status, error_message = :error
             WHERE execution_id = :eid
        """),
        {**stats, "status": status, "error": error[:1000] if error else None, "eid": execution_id},
    )


def save_issues(conn, execution_id: int, source_id: int, table: str, issues: list[dict]):
    """Insert issues found by the Python validation step."""
    if not issues:
        return
    conn.execute(
        text("""
            INSERT INTO data_quality_issues
                (execution_id, source_id, table_name, record_identifier, column_name,
                 rule_name, issue_type, description, severity)
            VALUES (:eid, :sid, :table, :record_identifier, :column_name,
                    :rule_name, :issue_type, :description, :severity)
        """),
        [{**i, "eid": execution_id, "sid": source_id, "table": table} for i in issues],
    )


# ---------------------------------------------------------------------
# Staging -> production
# ---------------------------------------------------------------------
def load_to_staging(conn, dataset: str, df: pd.DataFrame, execution_id: int):
    """Empty the staging table and bulk-insert the validated batch."""
    staging = LOAD_PLANS[dataset]["staging"]
    # DELETE (not TRUNCATE): TRUNCATE is DDL and would auto-commit our transaction.
    conn.execute(text(f"DELETE FROM {staging}"))
    batch = df.copy()
    batch.insert(0, "execution_id", execution_id)
    batch.to_sql(staging, con=conn, if_exists="append", index=False, method="multi", chunksize=500)


def load_to_production(conn, dataset: str, execution_id: int, source_id: int) -> dict:
    """Run resolve -> check -> upsert -> mark. Returns counts for the execution log."""
    plan = LOAD_PLANS[dataset]
    stg, target = plan["staging"], plan["target"]
    params = {"eid": execution_id}

    for sql in plan["resolve"]:
        conn.execute(text(sql), params)

    issues_found = 0
    for check in plan["checks"]:
        where = f"s.execution_id = :eid AND s.load_status = 'PENDING' AND {check['condition']}"
        result = conn.execute(text(f"""
            INSERT INTO data_quality_issues
                (execution_id, source_id, table_name, record_identifier, column_name,
                 rule_name, issue_type, description, severity)
            SELECT :eid, :sid, :tbl, {check['identifier']}, :col, :rule, :itype, {check['description']}, :sev
              FROM {stg} s {check['join']}
             WHERE {where}
        """), {**params, "sid": source_id, "tbl": target, "col": check["column"], "rule": check["rule"],
               "itype": check["issue_type"], "sev": check["severity"]})
        issues_found += result.rowcount
        conn.execute(text(f"UPDATE {stg} s {check['join']} SET s.load_status = 'REJECTED' WHERE {where}"), params)

    rejected = conn.execute(
        text(f"SELECT COUNT(*) FROM {stg} WHERE execution_id = :eid AND load_status = 'REJECTED'"), params
    ).scalar()
    to_load = conn.execute(
        text(f"SELECT COUNT(*) FROM {stg} WHERE execution_id = :eid AND load_status = 'PENDING'"), params
    ).scalar()
    # Rows whose key is not in production yet will be INSERTED; the rest UPDATE existing rows.
    new_rows = conn.execute(text(f"""
        SELECT COUNT(*)
          FROM {stg} s
          LEFT JOIN {target} t ON {plan['match_existing']}
         WHERE s.execution_id = :eid AND s.load_status = 'PENDING' AND t.{plan['target_pk']} IS NULL
    """), params).scalar()

    conn.execute(text(plan["upsert"]), params)
    conn.execute(text(f"UPDATE {stg} SET load_status = 'LOADED' "
                      f"WHERE execution_id = :eid AND load_status = 'PENDING'"), params)

    return {"inserted": new_rows, "updated": to_load - new_rows, "rejected": rejected, "errors": issues_found}

