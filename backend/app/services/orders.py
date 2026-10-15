from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from ..models import OrderItem, OrderSummary, Payment, Product
from .common import paginate, raise_for_db_error


def list_orders(db: Session, search: str | None, status: str | None, payment_status: str | None,
                customer_id: int | None, date_from: date | None, date_to: date | None,
                page: int, page_size: int) -> dict:
    query = select(OrderSummary)
    if search:
        query = query.where(OrderSummary.order_number.like(f"%{search}%"))
    if status:
        query = query.where(OrderSummary.status == status)
    if payment_status:
        query = query.where(OrderSummary.payment_status == payment_status)
    if customer_id:
        query = query.where(OrderSummary.customer_id == customer_id)
    # Half-open date range (>= from, < to + 1 day) so an index on order_date can be used
    if date_from:
        query = query.where(OrderSummary.order_date >= date_from)
    if date_to:
        query = query.where(OrderSummary.order_date < date_to + timedelta(days=1))
    query = query.order_by(OrderSummary.order_date.desc(), OrderSummary.order_id.desc())
    return paginate(db, query, page, page_size)


def get_order(db: Session, order_id: int) -> dict:
    order = db.get(OrderSummary, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    items = db.execute(
        select(OrderItem.order_item_id, Product.sku, Product.product_name, OrderItem.quantity,
               OrderItem.unit_price, OrderItem.discount_pct, OrderItem.line_total)
        .join(Product, Product.product_id == OrderItem.product_id)
        .where(OrderItem.order_id == order_id)
        .order_by(OrderItem.order_item_id)
    ).mappings().all()
    payments = db.scalars(
        select(Payment).where(Payment.order_id == order_id).order_by(Payment.payment_date)
    ).all()

    data = {c.name: getattr(order, c.name) for c in OrderSummary.__table__.columns}
    return {**data, "items": [dict(i) for i in items], "payments": payments}


def update_status(db: Session, order_id: int, new_status: str) -> dict:
    """Delegates the rules (allowed transitions) to the stored procedure."""
    try:
        row = db.execute(text("CALL sp_update_order_status(:id, :status)"),
                         {"id": order_id, "status": new_status}).mappings().first()
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        raise_for_db_error(exc)
    return dict(row)
