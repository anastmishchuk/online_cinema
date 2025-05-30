from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.movies.models import Genre, movie_genres
from src.movies.schemas import GenreCreate, GenreUpdate


async def get_genres_with_movie_count(db: AsyncSession):
    stmt = (
        select(
            Genre.id,
            Genre.name,
            func.count(movie_genres.c.movie_id).label("movie_count")
        )
        .join(movie_genres, Genre.id == movie_genres.c.genre_id)
        .group_by(Genre.id)
        .order_by(Genre.name)
    )
    result = await db.execute(stmt)
    return result.all()


async def get_genre_by_id(db: AsyncSession, genre_id: int) -> Genre:
    result = await db.execute(select(Genre).where(Genre.id == genre_id))
    return result.scalar_one_or_none()


async def create_genre(db: AsyncSession, genre_in: GenreCreate) -> Genre:
    genre = Genre(**genre_in.dict())
    db.add(genre)
    await db.commit()
    await db.refresh(genre)
    return genre


async def update_genre(db: AsyncSession, genre_id: int, genre_in: GenreUpdate):
    genre = await get_genre_by_id(db, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre is not found")

    if genre_in.name is not None:
        genre.name = genre_in.name

    await db.commit()
    await db.refresh(genre)
    return genre


async def delete_genre(db: AsyncSession, genre_id: int) -> None:
    genre = await get_genre_by_id(db, genre_id)
    await db.delete(genre)
    await db.commit()
