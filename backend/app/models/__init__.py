"""Importing this package registers every ORM model with SQLAlchemy."""

from .customer import Customer
from .etl import DataSource, EtlExecutionLog, EtlJob
from .monitoring import AuditLog, DataQualityIssue
from .order import Order, OrderItem
from .organization import Department, Employee
from .payment import Payment
from .product import Product
from .views import Customer360, OrderSummary, ProductPerformance

__all__ = [
    "Customer", "DataSource", "EtlExecutionLog", "EtlJob", "AuditLog", "DataQualityIssue",
    "Order", "OrderItem", "Department", "Employee", "Payment", "Product",
    "Customer360", "OrderSummary", "ProductPerformance",
]
