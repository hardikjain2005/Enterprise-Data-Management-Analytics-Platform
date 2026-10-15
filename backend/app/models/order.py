from datetime import datetime

from sqlalchemy import Computed, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .product import Product


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(primary_key=True)
    order_number: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.customer_id"))
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.employee_id"))
    order_date: Mapped[datetime]
    status: Mapped[str] = mapped_column(String(20))
    order_total: Mapped[float] = mapped_column(Numeric(12, 2))   # maintained by triggers

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    quantity: Mapped[int]
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2))
    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2))
    # Generated column: MySQL calculates it, the application never writes it.
    line_total: Mapped[float] = mapped_column(
        Numeric(12, 2), Computed("ROUND(quantity * unit_price * (1 - discount_pct / 100), 2)", persisted=True)
    )

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()
