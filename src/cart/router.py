from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.config.database import get_async_db
from src.users.dependencies import get_current_user
from src.users.models import User

from src.cart.schemas import CartMovieOut
from src.cart.services import (
    clear_cart,
    list_cart_movies
)


router = APIRouter()


@router.get("/", response_model=List[CartMovieOut])
async def get_user_cart(
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user)
):
    return await list_cart_movies(db, user)


@router.delete("/clear")
async def clear_user_cart(
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
):
    await clear_cart(db, user)
    return {"detail": "Cart cleared"}
