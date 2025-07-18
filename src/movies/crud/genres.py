from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Genre, MoviesGenresModel, Movie
from ..schemas import GenreCreate, GenreUpdate


async def get_genres_with_movie_count(db: AsyncSession):
    stmt = (
        select(
            Genre.id,
            Genre.name,
            func.count(MoviesGenresModel.c.movie_id).label("movie_count")
        )
        .outerjoin(MoviesGenresModel, Genre.id == MoviesGenresModel.c.genre_id)
        .group_by(Genre.id)
        .order_by(Genre.name)
    )
    result = await db.execute(stmt)
    return result.all()


async def get_genre_by_id(db: AsyncSession, genre_id: int) -> Genre | None:
    genre_result = await db.execute(select(Genre).where(Genre.id == genre_id))
    genre = genre_result.scalar_one_or_none()

    if not genre:
        return None

    count_result = await db.execute(
        select(func.count(MoviesGenresModel.c.movie_id))
        .where(MoviesGenresModel.c.genre_id == genre_id)
    )
    movie_count = count_result.scalar()

    genre.movie_count = movie_count
    return genre


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
