from datetime import date, timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from ..models import Order, Payment
from .common import paginate, raise_for_db_error


def list_payments(db: Session, search: str | None, status: str | None, method: str | None,
                  date_from: date | None, date_to: date | None, page: int, page_size: int) -> dict:
    query = (
        select(Payment.payment_id, Payment.payment_reference, Payment.order_id, Order.order_number,
               Payment.payment_date, Payment.amount, Payment.payment_method, Payment.status)
        .join(Order, Order.order_id == Payment.order_id)
    )
    if search:
        query = query.where((Payment.payment_reference.like(f"%{search}%")) |
                            (Order.order_number.like(f"%{search}%")))
    if status:
        query = query.where(Payment.status == status)
    if method:
        query = query.where(Payment.payment_method == method)
    if date_from:
        query = query.where(Payment.payment_date >= date_from)
    if date_to:
        query = query.where(Payment.payment_date < date_to + timedelta(days=1))
    query = query.order_by(Payment.payment_date.desc(), Payment.payment_id.desc())
    return paginate(db, query, page, page_size)


def record_payment(db: Session, order_id: int, amount: float, method: str, reference: str) -> dict:
    """
    The stored procedure sp_record_payment does the work inside a TRANSACTION
    (lock order row -> validate -> insert -> commit, or rollback on any error).
    """
    try:
        db.execute(text("CALL sp_record_payment(:order_id, :amount, :method, :ref, @payment_id)"),
                   {"order_id": order_id, "amount": amount, "method": method, "ref": reference})
        payment_id = db.execute(text("SELECT @payment_id")).scalar()
        balance = db.execute(text("SELECT fn_order_balance(:id)"), {"id": order_id}).scalar()
        db.commit()
    except DBAPIError as exc:
        db.rollback()
        raise_for_db_error(exc)
    return {"payment_id": payment_id, "order_id": order_id, "remaining_balance": balance}
