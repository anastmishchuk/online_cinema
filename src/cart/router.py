from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_async_db
from ..users.dependencies import get_current_user
from ..users.models import User

from .schemas import CartMovieOut
from .service import (
    clear_cart,
    list_cart_movies,
    remove_movie_from_cart
)


router = APIRouter()


@router.get("/", response_model=List[CartMovieOut])
async def get_user_cart(
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user)
):
    return await list_cart_movies(db, user)


@router.delete("/{movie_id}/remove")
async def remove_from_cart_in_cart_page(
    movie_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
):
    await remove_movie_from_cart(db, user, movie_id)
    return {"detail": "Movie removed from cart"}


@router.delete("/clear")
async def clear_user_cart(
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(get_current_user),
):
    await clear_cart(db, user)
    return {"detail": "Cart cleared"}
