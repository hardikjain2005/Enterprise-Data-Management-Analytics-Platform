from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.analytics import CustomerAnalytics, SalesAnalytics
from ..services import analytics as service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/sales", response_model=SalesAnalytics)
def sales(db: Session = Depends(get_db)):
    """Monthly sales (with running total and growth), category split, payment methods, top products."""
    return service.sales(db)


@router.get("/customers", response_model=CustomerAnalytics)
def customers(db: Session = Depends(get_db)):
    """Segments, tiers, top customers and new customers per month."""
    return service.customers(db)
