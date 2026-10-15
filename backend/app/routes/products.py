from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import Page
from ..schemas.products import ProductListItem
from ..services import products as service

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=Page[ProductListItem])
def list_products(
    search: str | None = Query(None, description="Matches product name or SKU"),
    category: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_products(db, search, category, page, page_size)


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)):
    return service.list_categories(db)
