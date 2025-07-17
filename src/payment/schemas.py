from datetime import datetime
from enum import Enum
from typing import List
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal


class PaymentStatusSchema(str, Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"


class PaymentCreateSchema(BaseModel):
    order_id: int
    amount: Decimal = Field(..., gt=0, description="Total payment amount in USD")
    external_payment_id: str | None = Field(default=None, description="ID from external payment provider")


class PaymentSessionResponseSchema(BaseModel):
    checkout_url: str
    payment_id: int


class PaymentItemSchema(BaseModel):
    order_item_id: int
    price_at_payment: Decimal

    model_config = ConfigDict(from_attributes=True)


class PaymentResponseSchema(BaseModel):
    id: int
    order_id: int
    amount: Decimal
    status: PaymentStatusSchema
    created_at: datetime
    external_payment_id: str | None
    items: List[PaymentItemSchema] = []

    model_config = ConfigDict(from_attributes=True)


class PaymentHistoryItemSchema(PaymentResponseSchema):
    pass
