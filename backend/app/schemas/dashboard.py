from datetime import datetime

from pydantic import BaseModel


class RecentExecution(BaseModel):
    execution_id: int
    job_name: str
    started_at: datetime
    status: str
    records_read: int
    records_rejected: int


class StatusCount(BaseModel):
    status: str
    count: int


class DashboardSummary(BaseModel):
    total_customers: int
    total_products: int
    total_orders: int
    total_revenue: float
    total_payments: float
    outstanding_balance: float
    etl_runs: int
    failed_etl_runs: int
    open_quality_issues: int
    critical_quality_issues: int
    orders_by_status: list[StatusCount]
    recent_etl_executions: list[RecentExecution]
