from typing import Literal, List

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.movies.models import Like, FavoriteMoviesModel, Comment, PurchasedMovie
from src.users.auth.service import get_user_by_id
from src.users.utils.email import send_email


async def like_or_dislike(
    db: AsyncSession,
    user_id: int,
    target_type: Literal["movie", "comment"],
    target_id: int,
    is_like: bool
):
    result = await db.execute(select(Like).where(
        and_(
            Like.user_id == user_id,
            Like.target_type == target_type,
            Like.target_id == target_id,
        )
    ))

    existing = result.scalar_one_or_none()

    if existing:
        existing.is_like = is_like
    else:
        new_like = Like(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            is_like=is_like
        )
        db.add(new_like)

    await db.commit()

    if target_type == "comment":
        comment = await get_comment_by_id(db, target_id)
        if comment and comment.user_id != user_id:
            parent_user_email = (await get_user_by_id(db, comment.user_id)).email
            liker_user = await get_user_by_id(db, user_id)
            subject = "You have new like to your comment"
            body = f"User {liker_user.email} {'liked' if is_like else 'disliked'} your comment."
            await send_email(parent_user_email, subject, body)

    return {
        "target_type": target_type,
        "target_id": target_id,
        "is_like": is_like
    }


async def add_movie_to_favorites(db: AsyncSession, user_id: int, movie_id: int):
    result = await db.execute(select(FavoriteMoviesModel).where(
        FavoriteMoviesModel.c.user_id == user_id,
        FavoriteMoviesModel.c.movie_id == movie_id,
    ))
    exists = result.first()

    if not exists:
        insert_stmt = FavoriteMoviesModel.insert().values(user_id=user_id, movie_id=movie_id)
        await db.execute(insert_stmt)
        await db.commit()


async def remove_movie_from_favorites(db: AsyncSession, user_id: int, movie_id: int):
    delete_stmt = FavoriteMoviesModel.delete().where(
        FavoriteMoviesModel.c.user_id == user_id,
        FavoriteMoviesModel.c.movie_id == movie_id,
    )
    await db.execute(delete_stmt)
    await db.commit()


async def get_comment_by_id(db: AsyncSession, comment_id: int) -> Comment | None:
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    return result.scalar_one_or_none()


async def is_movie_purchased(db: AsyncSession, user_id: int, movie_id: int) -> bool:
    result = await db.execute(select(PurchasedMovie).where(
        PurchasedMovie.user_id == user_id,
        PurchasedMovie.movie_id == movie_id
    ))
    return result.scalar_one_or_none() is not None


async def create_purchased_movie(
    db: AsyncSession,
    user_id: int,
    movie_id: int
) -> PurchasedMovie:
    if await is_movie_purchased(db, user_id, movie_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movie already purchased."
        )

    new_purchase = PurchasedMovie(user_id=user_id, movie_id=movie_id)
    db.add(new_purchase)
    await db.commit()
    await db.refresh(new_purchase)
    return new_purchase


async def get_user_purchased_movies(db: AsyncSession, user_id: int) -> List[PurchasedMovie]:
    result = await db.execute(select(PurchasedMovie).where(PurchasedMovie.user_id == user_id))
    return result.scalars().all()
