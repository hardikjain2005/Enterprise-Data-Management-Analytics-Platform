from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import Page
from ..schemas.customers import CustomerDetail, CustomerListItem
from ..services import customers as service

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=Page[CustomerListItem])
def list_customers(
    search: str | None = Query(None, description="Matches name, email or customer code"),
    segment: Literal["Retail", "SMB", "Corporate"] | None = None,
    tier: Literal["PLATINUM", "GOLD", "SILVER", "BRONZE"] | None = None,
    sort: Literal["total_spent", "total_orders", "signup_date", "customer_code"] = "total_spent",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_customers(db, search, segment, tier, sort, page, page_size)


@router.get("/{customer_id}", response_model=CustomerDetail)
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    """Customer details + summary from the stored procedure sp_get_customer_summary."""
    return service.get_customer(db, customer_id)
