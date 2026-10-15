from pydantic import BaseModel


class MonthlySales(BaseModel):
    sales_month: str
    total_orders: int
    cancelled_orders: int
    unique_customers: int
    revenue: float
    avg_order_value: float | None
    cumulative_revenue: float
    growth_pct: float | None


class CategorySales(BaseModel):
    category: str
    units_sold: int
    revenue: float
    revenue_share_pct: float


class MethodSales(BaseModel):
    payment_method: str
    payments: int
    amount: float


class TopProduct(BaseModel):
    sku: str
    product_name: str
    category: str
    units_sold: int
    revenue: float


class SalesAnalytics(BaseModel):
    monthly: list[MonthlySales]
    by_category: list[CategorySales]
    by_payment_method: list[MethodSales]
    top_products: list[TopProduct]


class SegmentStats(BaseModel):
    segment: str
    customers: int
    orders: int
    revenue: float
    avg_revenue_per_customer: float


class TierCount(BaseModel):
    tier: str
    customers: int


class TopCustomer(BaseModel):
    rank: int
    customer_id: int
    customer_code: str
    customer_name: str
    segment: str
    total_orders: int
    total_spent: float
    tier: str


class NewCustomers(BaseModel):
    month: str
    new_customers: int


class CustomerAnalytics(BaseModel):
    by_segment: list[SegmentStats]
    by_tier: list[TierCount]
    top_customers: list[TopCustomer]
    new_customers_by_month: list[NewCustomers]
