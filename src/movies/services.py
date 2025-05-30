from typing import Literal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.movies.models import Like, favorite_movies


async def like_or_dislike(
    db: AsyncSession,
    user_id: int,
    target_type: Literal["movie", "comment"],
    target_id: int,
    is_like: bool
):
    stmt = select(Like).where(
        and_(
            Like.user_id == user_id,
            Like.target_type == target_type,
            Like.target_id == target_id,
        )
    )

    result = await db.execute(stmt)
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

    return {
        "target_type": target_type,
        "target_id": target_id,
        "is_like": is_like
    }


async def add_movie_to_favorites(db: AsyncSession, user_id: int, movie_id: int):
    stmt = select(favorite_movies).where(
        favorite_movies.c.user_id == user_id,
        favorite_movies.c.movie_id == movie_id,
    )
    result = await db.execute(stmt)
    exists = result.first()

    if not exists:
        insert_stmt = favorite_movies.insert().values(user_id=user_id, movie_id=movie_id)
        await db.execute(insert_stmt)
        await db.commit()


async def remove_movie_from_favorites(db: AsyncSession, user_id: int, movie_id: int):
    delete_stmt = favorite_movies.delete().where(
        favorite_movies.c.user_id == user_id,
        favorite_movies.c.movie_id == movie_id,
    )
    await db.execute(delete_stmt)
    await db.commit()

