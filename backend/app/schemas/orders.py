from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from .common import ORMModel

OrderStatus = Literal["PENDING", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED"]


class OrderListItem(ORMModel):
    order_id: int
    order_number: str
    order_date: datetime
    status: str
    customer_id: int
    customer_code: str
    customer_name: str
    segment: str
    handled_by: str | None
    item_count: int
    order_total: float
    amount_paid: float
    balance_due: float
    payment_status: str


class OrderLine(ORMModel):
    order_item_id: int
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    discount_pct: float
    line_total: float


class OrderPayment(ORMModel):
    payment_id: int
    payment_reference: str
    payment_date: datetime
    amount: float
    payment_method: str
    status: str


class OrderDetail(OrderListItem):
    items: list[OrderLine]
    payments: list[OrderPayment]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderStatusResult(BaseModel):
    order_id: int
    order_number: str
    old_status: str
    new_status: str
