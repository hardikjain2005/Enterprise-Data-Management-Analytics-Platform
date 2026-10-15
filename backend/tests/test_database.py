"""Tests for constraints, triggers, functions and stored procedures."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.database import engine
from tests.conftest import scalar


def mysql_error_code(exc_info) -> int:
    return exc_info.value.orig.args[0]


def make_order(conn) -> int:
    """Create a test customer, product and empty order (inside the rolled-back transaction)."""
    conn.execute(text("""INSERT INTO customers (customer_code, first_name, last_name, email, city, country,
                                                segment, signup_date)
                         VALUES ('TEST-C1', '  ada ', 'Lovelace', '  ADA@Example.COM ', 'Pune', 'India',
                                 'Retail', '2025-01-01')"""))
    customer_id = scalar(conn, "SELECT LAST_INSERT_ID()")
    conn.execute(text("INSERT INTO products (sku, product_name, category, unit_price, stock_quantity) "
                      "VALUES ('TEST-P1', 'Test Widget', 'Test', 1000, 10)"))
    conn.execute(text("INSERT INTO orders (order_number, customer_id, order_date, status) "
                      "VALUES ('TEST-O1', :c, NOW(), 'PENDING')"), {"c": customer_id})
    return scalar(conn, "SELECT LAST_INSERT_ID()")


# ------------------------------------------------------------------ constraints
def test_check_constraint_rejects_negative_price(conn):
    with pytest.raises(DBAPIError) as exc:
        conn.execute(text("INSERT INTO products (sku, product_name, category, unit_price) "
                          "VALUES ('TEST-NEG', 'Bad', 'Test', -5)"))
    assert mysql_error_code(exc) == 3819          # Check constraint violated


def test_foreign_key_rejects_unknown_customer(conn):
    with pytest.raises(DBAPIError) as exc:
        conn.execute(text("INSERT INTO orders (order_number, customer_id, order_date) "
                          "VALUES ('TEST-FK', 99999999, NOW())"))
    assert mysql_error_code(exc) == 1452          # FK constraint fails


def test_unique_constraint_rejects_duplicate_email(conn):
    existing = scalar(conn, "SELECT email FROM customers LIMIT 1")
    with pytest.raises(DBAPIError) as exc:
        conn.execute(text("INSERT INTO customers (customer_code, first_name, last_name, email, city, country, "
                          "segment, signup_date) VALUES ('TEST-DUP', 'A', 'B', :e, 'X', 'India', 'Retail', "
                          "'2025-01-01')"), {"e": existing})
    assert mysql_error_code(exc) == 1062          # Duplicate entry


# ------------------------------------------------------------------ triggers
def test_before_insert_trigger_cleans_customer(conn):
    make_order(conn)
    row = conn.execute(text("SELECT first_name, email FROM customers WHERE customer_code = 'TEST-C1'")).one()
    assert row.first_name == "ada"                # trimmed (re-casing is done by the ETL, not the trigger)
    assert row.email == "ada@example.com"         # trimmed + lower-cased


def test_future_signup_date_is_rejected(conn):
    with pytest.raises(DBAPIError) as exc:
        conn.execute(text("INSERT INTO customers (customer_code, first_name, last_name, email, city, country, "
                          "segment, signup_date) VALUES ('TEST-F', 'A', 'B', 'f@x.com', 'X', 'India', 'Retail', "
                          "DATE_ADD(CURDATE(), INTERVAL 1 DAY))"))
    assert mysql_error_code(exc) == 1644          # SIGNAL from the trigger


def test_order_total_trigger_tracks_items(conn):
    order_id = make_order(conn)
    product_id = scalar(conn, "SELECT product_id FROM products WHERE sku = 'TEST-P1'")
    conn.execute(text("INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct) "
                      "VALUES (:o, :p, 3, 1000, 10)"), {"o": order_id, "p": product_id})
    assert scalar(conn, "SELECT order_total FROM orders WHERE order_id = :o", o=order_id) == 2700   # 3*1000*0.9

    conn.execute(text("UPDATE order_items SET quantity = 5 WHERE order_id = :o"), {"o": order_id})
    assert scalar(conn, "SELECT order_total FROM orders WHERE order_id = :o", o=order_id) == 4500

    conn.execute(text("DELETE FROM order_items WHERE order_id = :o"), {"o": order_id})
    assert scalar(conn, "SELECT order_total FROM orders WHERE order_id = :o", o=order_id) == 0


def test_audit_trigger_records_old_and_new_values(conn):
    customer_id = scalar(conn, "SELECT MIN(customer_id) FROM customers")
    old_city = scalar(conn, "SELECT city FROM customers WHERE customer_id = :c", c=customer_id)
    conn.execute(text("UPDATE customers SET city = 'Test City' WHERE customer_id = :c"), {"c": customer_id})
    audit = conn.execute(text("""SELECT action, changed_by, old_values->>'$.city' AS old_city,
                                        new_values->>'$.city' AS new_city
                                   FROM audit_logs WHERE table_name = 'customers' AND record_id = :c
                                  ORDER BY audit_id DESC LIMIT 1"""), {"c": customer_id}).one()
    assert (audit.action, audit.changed_by, audit.old_city, audit.new_city) == \
           ("UPDATE", "pytest", old_city, "Test City")


def test_audit_trigger_ignores_no_op_update(conn):
    customer_id = scalar(conn, "SELECT MIN(customer_id) FROM customers")
    before = scalar(conn, "SELECT COUNT(*) FROM audit_logs")
    conn.execute(text("UPDATE customers SET city = city WHERE customer_id = :c"), {"c": customer_id})
    assert scalar(conn, "SELECT COUNT(*) FROM audit_logs") == before


def test_audit_logs_are_append_only(conn):
    with pytest.raises(DBAPIError) as exc:
        conn.execute(text("UPDATE audit_logs SET changed_by = 'hacker' LIMIT 1"))
    assert mysql_error_code(exc) == 1644
    with pytest.raises(DBAPIError):
        conn.execute(text("DELETE FROM audit_logs LIMIT 1"))


# ------------------------------------------------------------------ functions
def test_functions_agree_with_views(conn):
    row = conn.execute(text("SELECT customer_id, total_spent, tier FROM vw_customer_360 "
                            "ORDER BY total_spent DESC LIMIT 1")).one()
    assert scalar(conn, "SELECT fn_customer_total_spent(:c)", c=row.customer_id) == row.total_spent
    assert scalar(conn, "SELECT fn_customer_tier(:c)", c=row.customer_id) == row.tier == "PLATINUM"

    order = conn.execute(text("SELECT order_id, balance_due FROM vw_order_summary LIMIT 1")).one()
    assert scalar(conn, "SELECT fn_order_balance(:o)", o=order.order_id) == order.balance_due


def test_order_totals_reconcile_with_lines(conn):
    mismatches = scalar(conn, """SELECT COUNT(*) FROM (
                                    SELECT o.order_id FROM orders o JOIN order_items oi ON oi.order_id = o.order_id
                                    GROUP BY o.order_id, o.order_total
                                    HAVING o.order_total <> SUM(oi.line_total)) x""")
    assert mismatches == 0


# ------------------------------------------------------------------ procedures
def test_sp_update_order_status_valid_and_invalid(conn):
    order_id = make_order(conn)
    row = conn.execute(text("CALL sp_update_order_status(:o, 'PROCESSING')"), {"o": order_id}).mappings().one()
    assert (row["old_status"], row["new_status"]) == ("PENDING", "PROCESSING")

    with pytest.raises(DBAPIError) as exc:
        conn.execute(text("CALL sp_update_order_status(:o, 'PENDING')"), {"o": order_id})  # backwards
    assert "Invalid status transition" in str(exc.value)


def test_sp_sales_report_matches_view(conn):
    rows = conn.execute(text("CALL sp_sales_report('2026-01-01', '2026-04-01')")).mappings().all()
    assert [r["sales_month"] for r in rows] == ["2026-01", "2026-02", "2026-03"]
    view = conn.execute(text("SELECT revenue FROM vw_monthly_sales WHERE sales_month = '2026-02'")).scalar()
    assert rows[1]["revenue"] == view


def test_sp_run_data_quality_checks_does_not_duplicate(conn):
    conn.execute(text("CALL sp_run_data_quality_checks(@n)"))
    conn.execute(text("CALL sp_run_data_quality_checks(@n)"))
    assert scalar(conn, "SELECT @n") == 0         # second run finds nothing NEW


@pytest.fixture
def unpaid_order():
    """An open order with an outstanding balance; payments created by the test are removed afterwards."""
    with engine.begin() as c:
        order_id = c.execute(text("""SELECT order_id FROM vw_order_summary
                                      WHERE status IN ('PENDING', 'PROCESSING') AND balance_due > 10
                                      ORDER BY order_id LIMIT 1""")).scalar()
    yield order_id
    with engine.begin() as c:
        c.execute(text("SET @app_user = 'pytest'"))
        c.execute(text("DELETE FROM payments WHERE payment_reference LIKE 'PYTEST-%'"))


def test_sp_record_payment_commits_valid_payment(unpaid_order):
    with engine.connect() as c:
        balance = c.execute(text("SELECT fn_order_balance(:o)"), {"o": unpaid_order}).scalar()
        c.execute(text("CALL sp_record_payment(:o, 5.00, 'UPI', 'PYTEST-OK-1', @pid)"), {"o": unpaid_order})
        assert c.execute(text("SELECT @pid")).scalar() is not None
        assert c.execute(text("SELECT fn_order_balance(:o)"), {"o": unpaid_order}).scalar() == balance - 5


def test_sp_record_payment_rolls_back_overpayment(unpaid_order):
    with engine.connect() as c:
        before = c.execute(text("SELECT COUNT(*) FROM payments")).scalar()
        with pytest.raises(DBAPIError) as exc:
            c.execute(text("CALL sp_record_payment(:o, fn_order_balance(:o) + 1, 'UPI', 'PYTEST-OVER', @pid)"),
                      {"o": unpaid_order})
        assert "exceeds outstanding balance" in str(exc.value)
        assert c.execute(text("SELECT COUNT(*) FROM payments")).scalar() == before


def test_sp_record_payment_rolls_back_duplicate_reference(unpaid_order):
    existing = None
    with engine.connect() as c:
        existing = c.execute(text("SELECT payment_reference FROM payments LIMIT 1")).scalar()
        before = c.execute(text("SELECT COUNT(*) FROM payments")).scalar()
        with pytest.raises(DBAPIError) as exc:
            c.execute(text("CALL sp_record_payment(:o, 1, 'UPI', :ref, @pid)"), {"o": unpaid_order, "ref": existing})
        assert exc.value.orig.args[0] == 1062
        assert c.execute(text("SELECT COUNT(*) FROM payments")).scalar() == before
