from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import ORMModel

PaymentMethod = Literal["CARD", "UPI", "NET_BANKING", "BANK_TRANSFER", "WALLET"]


class PaymentListItem(ORMModel):
    payment_id: int
    payment_reference: str
    order_id: int
    order_number: str
    payment_date: datetime
    amount: float
    payment_method: str
    status: str


class PaymentCreate(BaseModel):
    """Request body for POST /api/payments (validated BEFORE it reaches MySQL)."""
    order_id: int = Field(gt=0)
    amount: float = Field(gt=0, description="Must not exceed the order's outstanding balance")
    payment_method: PaymentMethod
    payment_reference: str = Field(min_length=5, max_length=30, pattern=r"^[A-Za-z0-9-]+$")


class PaymentCreated(BaseModel):
    payment_id: int
    order_id: int
    remaining_balance: float
