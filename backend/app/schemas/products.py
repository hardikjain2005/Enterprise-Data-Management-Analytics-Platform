from .common import ORMModel


class ProductListItem(ORMModel):
    product_id: int
    sku: str
    product_name: str
    category: str
    unit_price: float
    stock_quantity: int
    orders_count: int
    units_sold: int
    revenue: float
    rank_in_category: int
