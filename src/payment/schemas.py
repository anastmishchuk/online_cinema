from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel, Field
from decimal import Decimal


class PaymentStatusSchema(str, Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"


class PaymentCreateSchema(BaseModel):
    order_id: int
    amount: Decimal = Field(..., gt=0, description="Total payment amount in USD")


class PaymentSessionResponseSchema(BaseModel):
    checkout_url: str
    payment_id: int


class PaymentItemSchema(BaseModel):
    order_item_id: int
    price_at_payment: Decimal

    class Config:
        orm_mode = True


class PaymentResponseSchema(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusSchema
    created_at: datetime
    external_payment_id: str | None
    items: List[PaymentItemSchema] = []

    class Config:
        orm_mode = True


class PaymentHistoryItemSchema(PaymentResponseSchema):
    pass
