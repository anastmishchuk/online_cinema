from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class CartItemRead(BaseModel):
    id: int
    movie_id: int
    added_at: datetime

    class Config:
        orm_mode = True

class CartRead(BaseModel):
    id: int
    user_id: int
    cart_items: List[CartItemRead] = []

    class Config:
        orm_mode = True


class CartItemCreate(BaseModel):
    movie_id: int


class CartCreate(BaseModel):
    user_id: int


class CartMovieOut(BaseModel):
    id: int
    title: str
    genre: Optional[str]
    release_year: int
    price: float
    added_at: datetime

    class Config:
        orm_mode = True