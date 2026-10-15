from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import Page
from ..schemas.payments import PaymentCreate, PaymentCreated, PaymentListItem, PaymentMethod
from ..services import payments as service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("", response_model=Page[PaymentListItem])
def list_payments(
    search: str | None = Query(None, description="Matches payment reference or order number"),
    status: Literal["PENDING", "COMPLETED", "FAILED", "REFUNDED"] | None = None,
    method: PaymentMethod | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_payments(db, search, status, method, date_from, date_to, page, page_size)


@router.post("", response_model=PaymentCreated, status_code=201)
def record_payment(body: PaymentCreate, db: Session = Depends(get_db)):
    """Records a payment through the transactional stored procedure sp_record_payment."""
    return service.record_payment(db, body.order_id, body.amount, body.payment_method, body.payment_reference)
