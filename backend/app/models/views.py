"""
Read-only models mapped onto the database VIEWS (views.sql).

SQLAlchemy can query a view exactly like a table; we only need to tell it
which column uniquely identifies a row. The API never writes to these.
"""

from datetime import date, datetime

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Customer360(Base):
    __tablename__ = "vw_customer_360"

    customer_id: Mapped[int] = mapped_column(primary_key=True)
    customer_code: Mapped[str] = mapped_column(String(20))
    customer_name: Mapped[str]
    email: Mapped[str]
    city: Mapped[str]
    country: Mapped[str]
    segment: Mapped[str]
    signup_date: Mapped[date]
    total_orders: Mapped[int]
    cancelled_orders: Mapped[int]
    total_spent: Mapped[float] = mapped_column(Numeric(12, 2))
    last_order_date: Mapped[datetime | None]
    days_since_last_order: Mapped[int | None]
    tier: Mapped[str]


class OrderSummary(Base):
    __tablename__ = "vw_order_summary"

    order_id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str]
    order_date: Mapped[datetime]
    status: Mapped[str]
    customer_id: Mapped[int]
    customer_code: Mapped[str]
    customer_name: Mapped[str]
    segment: Mapped[str]
    handled_by: Mapped[str | None]
    item_count: Mapped[int]
    order_total: Mapped[float] = mapped_column(Numeric(12, 2))
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2))
    balance_due: Mapped[float] = mapped_column(Numeric(12, 2))
    payment_status: Mapped[str]


class ProductPerformance(Base):
    __tablename__ = "vw_product_performance"

    product_id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str]
    product_name: Mapped[str]
    category: Mapped[str]
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    stock_quantity: Mapped[int]
    orders_count: Mapped[int]
    units_sold: Mapped[int]
    revenue: Mapped[float] = mapped_column(Numeric(12, 2))
    rank_in_category: Mapped[int]
