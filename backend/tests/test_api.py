"""API tests: every endpoint answers, filters work, errors are clean."""

import pytest
from sqlalchemy import text

from app.database import engine

LIST_ENDPOINTS = ["/api/customers", "/api/products", "/api/orders", "/api/payments",
                  "/api/data-quality/issues", "/api/etl/logs", "/api/audit-logs"]


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["database"] == "enterprise_data_platform"


@pytest.mark.parametrize("url", LIST_ENDPOINTS)
def test_list_endpoints_are_paginated(client, url):
    response = client.get(url, params={"page": 1, "page_size": 5})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "page_size"}
    assert len(body["items"]) <= 5 and body["total"] >= len(body["items"])


def test_page_size_is_validated(client):
    assert client.get("/api/customers", params={"page_size": 1000}).status_code == 422


def test_dashboard_matches_database(client):
    body = client.get("/api/dashboard/summary").json()
    with engine.connect() as c:
        customers = c.execute(text("SELECT COUNT(*) FROM customers")).scalar()
        failed = c.execute(text("SELECT COUNT(*) FROM etl_execution_logs WHERE status = 'FAILED'")).scalar()
    assert body["total_customers"] == customers
    assert body["failed_etl_runs"] == failed
    assert body["total_revenue"] > 0 and len(body["recent_etl_executions"]) > 0


def test_customer_filters_and_detail(client):
    corporate = client.get("/api/customers", params={"segment": "Corporate", "page_size": 100}).json()
    assert corporate["items"] and all(c["segment"] == "Corporate" for c in corporate["items"])

    top = corporate["items"][0]
    detail = client.get(f"/api/customers/{top['customer_id']}").json()
    assert detail["summary"]["total_spent"] == top["total_spent"]      # procedure == view
    assert client.get("/api/customers/99999999").status_code == 404


def test_order_filters_and_detail(client):
    pending = client.get("/api/orders", params={"status": "PENDING"}).json()
    assert all(o["status"] == "PENDING" for o in pending["items"])

    in_september = client.get("/api/orders", params={"date_from": "2026-09-01", "date_to": "2026-09-30",
                                                      "page_size": 100}).json()
    assert all("2026-09-01" <= o["order_date"][:10] <= "2026-09-30" for o in in_september["items"])

    order = client.get("/api/orders/1").json()
    assert round(sum(i["line_total"] for i in order["items"]), 2) == order["order_total"]


def test_invalid_status_transition_returns_400(client):
    delivered = client.get("/api/orders", params={"status": "DELIVERED", "page_size": 1}).json()["items"][0]
    response = client.patch(f"/api/orders/{delivered['order_id']}/status", json={"status": "PENDING"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid status transition"


def test_unknown_status_value_returns_422(client):
    assert client.patch("/api/orders/1/status", json={"status": "LOST"}).status_code == 422


def test_payment_validation_errors(client):
    cancelled = client.get("/api/orders", params={"status": "CANCELLED", "page_size": 1}).json()["items"][0]
    response = client.post("/api/payments", json={"order_id": cancelled["order_id"], "amount": 10,
                                                  "payment_method": "UPI", "payment_reference": "PYTEST-CXL"})
    assert response.status_code == 400
    assert "cancelled" in response.json()["detail"]
    # Pydantic validation happens before the database is touched
    assert client.post("/api/payments", json={"order_id": 1, "amount": -5, "payment_method": "UPI",
                                              "payment_reference": "PYTEST-NEG"}).status_code == 422


def test_record_payment_through_api(client):
    open_order = client.get("/api/orders", params={"payment_status": "UNPAID", "status": "PROCESSING"}).json()
    order = open_order["items"][0]
    try:
        response = client.post("/api/payments", json={"order_id": order["order_id"], "amount": 1.0,
                                                      "payment_method": "CARD", "payment_reference": "PYTEST-API-1"})
        assert response.status_code == 201
        assert response.json()["remaining_balance"] == round(order["balance_due"] - 1.0, 2)
        again = client.post("/api/payments", json={"order_id": order["order_id"], "amount": 1.0,
                                                   "payment_method": "CARD", "payment_reference": "PYTEST-API-1"})
        assert again.status_code == 409                                    # duplicate transaction
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM payments WHERE payment_reference LIKE 'PYTEST-%'"))


def test_analytics_endpoints(client):
    sales = client.get("/api/analytics/sales").json()
    months = sales["monthly"]
    assert months[-1]["cumulative_revenue"] == pytest.approx(sum(m["revenue"] for m in months))
    assert sum(c["revenue_share_pct"] for c in sales["by_category"]) == pytest.approx(100, abs=0.5)

    customers = client.get("/api/analytics/customers").json()
    assert [t["tier"] for t in customers["by_tier"]] == ["PLATINUM", "GOLD", "SILVER", "BRONZE"]
    assert customers["top_customers"][0]["rank"] == 1


def test_etl_and_data_quality_endpoints(client):
    jobs = client.get("/api/etl/jobs").json()
    assert [j["job_name"] for j in jobs][:2] == ["load_customers", "load_products"]
    failed = client.get("/api/etl/logs", params={"status": "FAILED"}).json()
    assert all(log["status"] == "FAILED" for log in failed["items"])

    summary = client.get("/api/data-quality/summary").json()
    assert summary["total_issues"] >= summary["open_issues"]
    critical = client.get("/api/data-quality/issues", params={"severity": "CRITICAL"}).json()
    assert all(i["severity"] == "CRITICAL" for i in critical["items"])


def test_resolve_and_reopen_issue(client):
    issue = client.get("/api/data-quality/issues", params={"status": "OPEN", "page_size": 1}).json()["items"][0]
    resolved = client.patch(f"/api/data-quality/issues/{issue['issue_id']}",
                            json={"resolution_status": "RESOLVED", "resolution_note": "pytest"}).json()
    assert resolved["resolution_status"] == "RESOLVED" and resolved["resolved_at"] is not None
    reopened = client.patch(f"/api/data-quality/issues/{issue['issue_id']}",
                            json={"resolution_status": "OPEN", "resolution_note": None}).json()
    assert reopened["resolution_status"] == "OPEN" and reopened["resolved_at"] is None
