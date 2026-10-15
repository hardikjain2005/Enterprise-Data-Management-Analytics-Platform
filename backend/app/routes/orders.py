from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import Page
from ..schemas.orders import OrderDetail, OrderListItem, OrderStatus, OrderStatusResult, OrderStatusUpdate
from ..services import orders as service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=Page[OrderListItem])
def list_orders(
    search: str | None = Query(None, description="Matches order number"),
    status: OrderStatus | None = None,
    payment_status: Literal["PAID", "PARTIALLY_PAID", "UNPAID", "NOT_APPLICABLE"] | None = None,
    customer_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_orders(db, search, status, payment_status, customer_id,
                               date_from, date_to, page, page_size)


@router.get("/{order_id}", response_model=OrderDetail)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return service.get_order(db, order_id)


@router.patch("/{order_id}/status", response_model=OrderStatusResult)
def update_order_status(order_id: int, body: OrderStatusUpdate, db: Session = Depends(get_db)):
    """Calls sp_update_order_status, which only allows valid transitions."""
    return service.update_status(db, order_id, body.status)
