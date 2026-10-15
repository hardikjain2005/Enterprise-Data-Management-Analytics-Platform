from fastapi import HTTPException
from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from ..models import Customer, Customer360, OrderSummary
from .common import paginate

SORTABLE = {
    "total_spent": Customer360.total_spent.desc(),
    "total_orders": Customer360.total_orders.desc(),
    "signup_date": Customer360.signup_date.desc(),
    "customer_code": Customer360.customer_code.asc(),
}


def list_customers(db: Session, search: str | None, segment: str | None, tier: str | None,
                   sort: str, page: int, page_size: int) -> dict:
    query = select(Customer360)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(Customer360.customer_name.like(pattern),
                                Customer360.email.like(pattern),
                                Customer360.customer_code.like(pattern)))
    if segment:
        query = query.where(Customer360.segment == segment)
    if tier:
        query = query.where(Customer360.tier == tier)
    query = query.order_by(SORTABLE.get(sort, SORTABLE["total_spent"]), Customer360.customer_id)
    return paginate(db, query, page, page_size)


def get_customer(db: Session, customer_id: int) -> dict:
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Stored procedure call: CALL returns a normal result set
    summary = db.execute(text("CALL sp_get_customer_summary(:id)"), {"id": customer_id}).mappings().first()

    recent = db.scalars(
        select(OrderSummary)
        .where(OrderSummary.customer_id == customer_id)
        .order_by(OrderSummary.order_date.desc())
        .limit(10)
    ).all()

    return {**{c: getattr(customer, c) for c in (
        "customer_id", "customer_code", "first_name", "last_name", "email", "phone",
        "city", "state", "country", "segment", "signup_date")},
        "summary": dict(summary), "recent_orders": recent}
