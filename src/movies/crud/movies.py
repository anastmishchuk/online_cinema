import uuid

from fastapi import HTTPException
from sqlalchemy import select, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload


from src.movies.models import (
    Movie,
    Star,
    Director,
    movie_stars,
    movie_directors,
    movie_genres
)
from src.movies.schemas import MovieCreate, MovieUpdate, MovieFilter


async def get_movies_filtered(db: AsyncSession, filters: MovieFilter):
    stmt = select(Movie).options(
        joinedload(Movie.stars),
        joinedload(Movie.directors),
    )

    conditions = []

    if filters.year is not None:
        conditions.append(Movie.year == filters.year)
    if filters.min_imdb is not None:
        conditions.append(Movie.imdb >= filters.min_imdb)
    if filters.max_imdb is not None:
        conditions.append(Movie.imdb <= filters.max_imdb)
    if filters.min_meta_score is not None:
        conditions.append(Movie.meta_score >= filters.min_meta_score)
    if filters.max_meta_score is not None:
        conditions.append(Movie.meta_score <= filters.max_meta_score)
    if filters.certification_id is not None:
        conditions.append(Movie.certification_id == filters.certification_id)

    if filters.search:
        stmt = stmt.outerjoin(movie_stars).outerjoin(Star)
        stmt = stmt.outerjoin(movie_directors).outerjoin(Director)
        conditions.append(
            or_(
                Movie.name.ilike(f"%{filters.search}%"),
                Movie.description.ilike(f"%{filters.search}%"),
                Star.name.ilike(f"%{filters.search}%"),
                Director.name.ilike(f"%{filters.search}%"),
            )
        )

    if conditions:
        stmt = stmt.where(and_(*conditions))

    # Sorting
    if filters.sort:
        sort_field = filters.sort.lstrip("-")
        order_field = getattr(Movie, sort_field, None)
        if order_field is not None:
            if filters.sort.startswith("-"):
                stmt = stmt.order_by(desc(order_field))
            else:
                stmt = stmt.order_by(asc(order_field))

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    stmt = stmt.offset(offset).limit(filters.page_size)

    result = await db.execute(stmt)
    return result.scalars().unique().all()


async def get_movie(db: AsyncSession, movie_id: int):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    return result.scalar_one_or_none()


async def get_movies(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(select(Movie).offset(skip).limit(limit))
    return result.scalars().all()


async def get_movies_by_genre_id(db: AsyncSession, genre_id: int):
    stmt = (
        select(Movie)
        .join(movie_genres, Movie.id == movie_genres.c.movie_id)
        .where(movie_genres.c.genre_id == genre_id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_movie(db: AsyncSession, movie: MovieCreate):
    new_movie = Movie(**movie.dict(), uuid=str(uuid.uuid4()))
    db.add(new_movie)
    await db.commit()
    await db.refresh(new_movie)
    return new_movie


async def update_movie(db: AsyncSession, movie_id: int, movie_in: MovieUpdate):
    movie = await get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie is not found")

    for key, value in movie_in.dict(exclude_unset=True).items():
        setattr(movie, key, value)

    await db.commit()
    await db.refresh(movie)
    return movie


"""
This function will be finished after Payment module
"""

# async def delete_movie(db: AsyncSession, movie_id: int):
#     movie = await get_movie(db, movie_id)
#     if not movie:
#         raise HTTPException(status_code=404, detail="Movie is not found")
#
#     # 👇 Check if any purchases exist for this movie
#     result = await db.execute(
#         select(models.Payment).where(models.Payment.movie_id == movie_id)
#     )
#     purchase = result.first()
#     if purchase:
#         raise HTTPException(status_code=400, detail="Cannot delete: movie has been purchased")
#
#     await db.delete(movie)
#     await db.commit()
