from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional


class CartItemRead(BaseModel):
    id: int
    movie_id: int
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)

class CartRead(BaseModel):
    id: int
    user_id: int
    cart_items: List[CartItemRead] = []

    model_config = ConfigDict(from_attributes=True)


class CartItemCreate(BaseModel):
    movie_id: int


class CartCreate(BaseModel):
    user_id: int


class CartMovieOut(BaseModel):
    id: int
    name: str
    genres: Optional[List[str]] = None
    release_year: int
    price: Decimal
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)