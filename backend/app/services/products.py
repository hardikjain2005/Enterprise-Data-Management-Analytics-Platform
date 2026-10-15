from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..models import Product, ProductPerformance
from .common import paginate


def list_products(db: Session, search: str | None, category: str | None,
                  page: int, page_size: int) -> dict:
    query = select(ProductPerformance)
    if search:
        pattern = f"%{search}%"
        query = query.where(or_(ProductPerformance.product_name.like(pattern),
                                ProductPerformance.sku.like(pattern)))
    if category:
        query = query.where(ProductPerformance.category == category)
    query = query.order_by(ProductPerformance.revenue.desc(), ProductPerformance.product_id)
    return paginate(db, query, page, page_size)


def list_categories(db: Session) -> list[str]:
    return list(db.scalars(select(Product.category).distinct().order_by(Product.category)))
