from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, constr, ConfigDict


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    canceled = "canceled"


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movie_id: int
    price_at_order: Decimal


class OrderItemCreate(BaseModel):
    movie_id: int
    price_at_order: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    status: OrderStatus
    total_amount: Optional[Decimal] = None
    items: List[OrderItemRead] = Field(default_factory=list)


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class RefundRequestCreate(BaseModel):
    reason: constr(min_length=10, max_length=500)
