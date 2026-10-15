from datetime import date, datetime

from .common import ORMModel


class CustomerListItem(ORMModel):
    customer_id: int
    customer_code: str
    customer_name: str
    email: str
    city: str
    country: str
    segment: str
    signup_date: date
    total_orders: int
    total_spent: float
    last_order_date: datetime | None
    tier: str


class CustomerSummary(ORMModel):
    """Row returned by the stored procedure sp_get_customer_summary."""
    customer_id: int
    customer_code: str
    customer_name: str
    segment: str
    total_orders: int
    cancelled_orders: int
    total_spent: float
    total_paid: float
    first_order_date: datetime | None
    last_order_date: datetime | None
    tier: str


class CustomerOrder(ORMModel):
    order_id: int
    order_number: str
    order_date: datetime
    status: str
    order_total: float
    payment_status: str


class CustomerDetail(ORMModel):
    customer_id: int
    customer_code: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    city: str
    state: str | None
    country: str
    segment: str
    signup_date: date
    summary: CustomerSummary
    recent_orders: list[CustomerOrder]
