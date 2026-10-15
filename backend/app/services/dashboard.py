from sqlalchemy import text
from sqlalchemy.orm import Session

# Scalar subqueries: each (SELECT ...) returns one value, so one round trip gives every KPI.
SUMMARY_SQL = text("""
    SELECT
        (SELECT COUNT(*) FROM customers)                                              AS total_customers,
        (SELECT COUNT(*) FROM products)                                               AS total_products,
        (SELECT COUNT(*) FROM orders)                                                 AS total_orders,
        (SELECT COALESCE(SUM(order_total), 0) FROM orders WHERE status <> 'CANCELLED') AS total_revenue,
        (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'COMPLETED')    AS total_payments,
        (SELECT COALESCE(SUM(balance_due), 0) FROM vw_order_summary
          WHERE status <> 'CANCELLED' AND balance_due > 0)                            AS outstanding_balance,
        (SELECT COUNT(*) FROM etl_execution_logs)                                     AS etl_runs,
        (SELECT COUNT(*) FROM etl_execution_logs WHERE status = 'FAILED')             AS failed_etl_runs,
        (SELECT COUNT(*) FROM data_quality_issues WHERE resolution_status = 'OPEN')   AS open_quality_issues,
        (SELECT COUNT(*) FROM data_quality_issues
          WHERE resolution_status = 'OPEN' AND severity = 'CRITICAL')                 AS critical_quality_issues
""")

STATUS_SQL = text("""
    SELECT status, COUNT(*) AS count
    FROM   orders
    GROUP BY status
    ORDER BY FIELD(status, 'PENDING', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED')
""")

RECENT_ETL_SQL = text("""
    SELECT l.execution_id, j.job_name, l.started_at, l.status, l.records_read, l.records_rejected
    FROM   etl_execution_logs l
    JOIN   etl_jobs j ON j.job_id = l.job_id
    ORDER BY l.started_at DESC, l.execution_id DESC
    LIMIT 8
""")


def get_summary(db: Session) -> dict:
    summary = dict(db.execute(SUMMARY_SQL).mappings().one())
    summary["orders_by_status"] = [dict(r) for r in db.execute(STATUS_SQL).mappings()]
    summary["recent_etl_executions"] = [dict(r) for r in db.execute(RECENT_ETL_SQL).mappings()]
    return summary
