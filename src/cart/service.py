from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from fastapi import HTTPException
from sqlalchemy.orm import joinedload

from ..users.models import User
from ..movies.models import Movie, PurchasedMovie

from .models import Cart, CartItem
from .schemas import CartMovieOut


async def check_movie_availability(db: AsyncSession, movie_id: int):
    result = await db.execute(select(Movie).where(
        Movie.id == movie_id
    ))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie is not available for purchase")


async def get_or_create_cart(db: AsyncSession, user: User) -> Cart:
    result = await db.execute(select(Cart).where(Cart.user_id == user.id))
    cart = result.scalar_one_or_none()
    if cart:
        return cart

    new_cart = Cart(user_id=user.id)
    db.add(new_cart)
    await db.commit()
    await db.refresh(new_cart)
    return new_cart


async def add_movie_to_cart(db: AsyncSession, user: User, movie_id: int) -> None:
    await check_movie_availability(db, movie_id)

    purchase_result = await db.execute(
        select(PurchasedMovie).where(
            PurchasedMovie.user_id == user.id,
            PurchasedMovie.movie_id == movie_id
        )
    )
    if purchase_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Movie already purchased")

    cart = await get_or_create_cart(db, user)

    item_result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.movie_id == movie_id)
    )
    if item_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Movie already in cart")

    db.add(CartItem(cart_id=cart.id, movie_id=movie_id))
    await db.commit()


async def remove_movie_from_cart(db: AsyncSession, user: User, movie_id: int) -> None:
    cart = await get_or_create_cart(db, user)

    result = await db.execute(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.movie_id == movie_id
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Movie not found in cart")

    await db.delete(item)
    await db.commit()


async def list_cart_movies(db: AsyncSession, user: User) -> list[CartMovieOut]:
    cart = await get_or_create_cart(db, user)

    result = await db.execute(
        select(CartItem)
        .options(joinedload(CartItem.movie).subqueryload(Movie.genres))
        .where(CartItem.cart_id == cart.id)
    )
    all_items = result.scalars().all()
    unique_items = {item.movie.id: item for item in all_items if item.movie}
    items = list(unique_items.values())

    return [
        CartMovieOut(
            id=item.movie.id,
            name=item.movie.name,
            price=item.movie.price,
            release_year=item.movie.year,
            genres=[genre.name for genre in item.movie.genres] if item.movie.genres else [],
            added_at=item.added_at,
        )
        for item in items if item.movie
    ]


async def clear_cart(db: AsyncSession, user: User) -> None:
    cart = await get_or_create_cart(db, user)
    await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    await db.commit()
