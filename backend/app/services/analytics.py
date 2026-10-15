"""Analytics queries. Written as plain SQL on purpose: they use window functions and views."""

from sqlalchemy import text
from sqlalchemy.orm import Session

MONTHLY_SQL = text("""
    SELECT sales_month, total_orders, cancelled_orders, unique_customers, revenue, avg_order_value,
           SUM(revenue) OVER (ORDER BY sales_month)                        AS cumulative_revenue,
           ROUND(100 * (revenue - LAG(revenue) OVER (ORDER BY sales_month))
                     / LAG(revenue) OVER (ORDER BY sales_month), 1)        AS growth_pct
    FROM   vw_monthly_sales
    ORDER BY sales_month
""")

CATEGORY_SQL = text("""
    SELECT category,
           SUM(units_sold)                                         AS units_sold,
           SUM(revenue)                                            AS revenue,
           ROUND(100 * SUM(revenue) / SUM(SUM(revenue)) OVER (), 1) AS revenue_share_pct
    FROM   vw_product_performance
    GROUP BY category
    ORDER BY revenue DESC
""")

METHOD_SQL = text("""
    SELECT payment_method, COUNT(*) AS payments, SUM(amount) AS amount
    FROM   payments
    WHERE  status = 'COMPLETED'
    GROUP BY payment_method
    ORDER BY amount DESC
""")

TOP_PRODUCTS_SQL = text("""
    SELECT sku, product_name, category, units_sold, revenue
    FROM   vw_product_performance
    ORDER BY revenue DESC
    LIMIT 10
""")

SEGMENT_SQL = text("""
    SELECT segment,
           COUNT(*)                     AS customers,
           SUM(total_orders)            AS orders,
           SUM(total_spent)             AS revenue,
           ROUND(AVG(total_spent), 2)   AS avg_revenue_per_customer
    FROM   vw_customer_360
    GROUP BY segment
    ORDER BY revenue DESC
""")

TIER_SQL = text("""
    SELECT tier, COUNT(*) AS customers
    FROM   vw_customer_360
    GROUP BY tier
    ORDER BY FIELD(tier, 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE')
""")

TOP_CUSTOMERS_SQL = text("""
    SELECT RANK() OVER (ORDER BY total_spent DESC) AS `rank`,
           customer_id, customer_code, customer_name, segment, total_orders, total_spent, tier
    FROM   vw_customer_360
    ORDER BY total_spent DESC
    LIMIT 10
""")

NEW_CUSTOMERS_SQL = text("""
    SELECT DATE_FORMAT(signup_date, '%Y-%m') AS month, COUNT(*) AS new_customers
    FROM   customers
    GROUP BY DATE_FORMAT(signup_date, '%Y-%m')
    ORDER BY month
""")


def _rows(db: Session, sql) -> list[dict]:
    return [dict(r) for r in db.execute(sql).mappings()]


def sales(db: Session) -> dict:
    return {"monthly": _rows(db, MONTHLY_SQL), "by_category": _rows(db, CATEGORY_SQL),
            "by_payment_method": _rows(db, METHOD_SQL), "top_products": _rows(db, TOP_PRODUCTS_SQL)}


def customers(db: Session) -> dict:
    return {"by_segment": _rows(db, SEGMENT_SQL), "by_tier": _rows(db, TIER_SQL),
            "top_customers": _rows(db, TOP_CUSTOMERS_SQL),
            "new_customers_by_month": _rows(db, NEW_CUSTOMERS_SQL)}
