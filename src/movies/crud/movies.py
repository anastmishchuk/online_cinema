import uuid

from fastapi import HTTPException
from sqlalchemy import select, or_, and_, desc, asc
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from cart.models import CartItem
from ..models import (
    Movie,
    Star,
    Director,
    MoviesDirectorsModel,
    MoviesGenresModel,
    MoviesStarsModel,
    FavoriteMoviesModel,
    PurchasedMovie, Genre, Certification
)
from ..schemas import MovieCreate, MovieUpdate, MovieFilter


async def get_movies_filtered(
        db: AsyncSession,
        filters: MovieFilter,
        user_id: int | None = None
):
    stmt = select(Movie).options(
        joinedload(Movie.certification),
        selectinload(Movie.stars),
        selectinload(Movie.directors),
        selectinload(Movie.genres),
    )

    conditions = []

    if user_id is not None:
        favorites_subquery = select(Movie).join(
            FavoriteMoviesModel,
            Movie.id == FavoriteMoviesModel.c.movie_id
        ).where(
            FavoriteMoviesModel.c.user_id == user_id
        )
        conditions.append(Movie.id.in_(favorites_subquery))

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
        search_conditions = [
            Movie.name.ilike(f"%{filters.search}%"),
            Movie.description.ilike(f"%{filters.search}%"),
        ]

        star_subquery = select(MoviesStarsModel.c.movie_id).join(Star).where(
            Star.name.ilike(f"%{filters.search}%")
        )
        search_conditions.append(Movie.id.in_(star_subquery))

        director_subquery = select(MoviesDirectorsModel.c.movie_id).join(Director).where(
            Director.name.ilike(f"%{filters.search}%")
        )
        search_conditions.append(Movie.id.in_(director_subquery))

        conditions.append(or_(*search_conditions))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    if filters.sort:
        sort_field = filters.sort.lstrip("-")
        order_field = getattr(Movie, sort_field, None)
        if order_field is not None:
            if filters.sort.startswith("-"):
                stmt = stmt.order_by(desc(order_field))
            else:
                stmt = stmt.order_by(asc(order_field))

    offset = (filters.page - 1) * filters.page_size
    stmt = stmt.offset(offset).limit(filters.page_size)
    result = await db.execute(stmt)
    movies = result.scalars().unique().all()

    return movies


async def get_movie(db: AsyncSession, movie_id: int):
    result = await db.execute(
        select(Movie)
        .where(Movie.id == movie_id)
        .options(
            joinedload(Movie.certification),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars)
        )
    )
    return result.scalar_one_or_none()


async def get_movies(db: AsyncSession, skip: int = 0, limit: int = 10):
    result = await db.execute(
        select(Movie)
        .offset(skip)
        .limit(limit)
        .options(
            joinedload(Movie.certification),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars)
        )
    )
    return result.scalars().all()


async def get_movies_by_genre_id(db: AsyncSession, genre_id: int):
    stmt = (
        select(Movie)
        .join(MoviesGenresModel, Movie.id == MoviesGenresModel.c.movie_id)
        .where(MoviesGenresModel.c.genre_id == genre_id)
        .options(
            joinedload(Movie.certification),
            selectinload(Movie.genres),
            selectinload(Movie.directors),
            selectinload(Movie.stars),
        )
    )
    result = await db.execute(stmt)
    return result.unique().scalars().all()


async def create_movie(db: AsyncSession, movie: MovieCreate) -> Movie:
    certification = await db.get(Certification, movie.certification_id)
    if not certification:
        raise HTTPException(status_code=400, detail="Certification not found")

    core_fields = movie.dict(exclude={"genre_ids", "director_ids", "star_ids"})
    new_movie = Movie(**core_fields, uuid=uuid.uuid4())
    db.add(new_movie)
    await db.flush()

    if movie.genre_ids:
        await db.execute(
            insert(MoviesGenresModel).values([
                {"movie_id": new_movie.id, "genre_id": genre_id}
                for genre_id in movie.genre_ids
            ])
        )

    if movie.director_ids:
        await db.execute(
            insert(MoviesDirectorsModel).values([
                {"movie_id": new_movie.id, "director_id": director_id}
                for director_id in movie.director_ids
            ])
        )

    if movie.star_ids:
        await db.execute(
            insert(MoviesStarsModel).values([
                {"movie_id": new_movie.id, "star_id": star_id}
                for star_id in movie.star_ids
            ])
        )

    await db.commit()

    result = await db.execute(
        select(Movie)
        .where(Movie.id == new_movie.id)
        .options(
            joinedload(Movie.certification),
            joinedload(Movie.genres),
            joinedload(Movie.directors),
            joinedload(Movie.stars)
        )
    )
    movie_with_relations = result.unique().scalar_one()
    return movie_with_relations


async def update_movie(movie_id: int, data: MovieUpdate, db: AsyncSession):
    result = await db.execute(
        select(Movie).where(Movie.id == movie_id)
        .options(
            joinedload(Movie.genres),
            joinedload(Movie.directors),
            joinedload(Movie.stars),
            joinedload(Movie.certification)
        )
    )
    movie = result.scalars().first()
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    for field, value in data.dict(
            exclude_unset=True,
            exclude={"genre_ids", "director_ids", "star_ids"}
    ).items():
        setattr(movie, field, value)

    if data.genre_ids is not None:
        genres = (await db.execute(
            select(Genre).where(Genre.id.in_(data.genre_ids))
        )).scalars().all()
        movie.genres = genres

    if data.director_ids is not None:
        directors = (await db.execute(
            select(Director).where(Director.id.in_(data.director_ids))
        )).scalars().all()
        movie.directors = directors

    if data.star_ids is not None:
        stars = (await db.execute(
            select(Star).where(Star.id.in_(data.star_ids))
        )).scalars().all()
        movie.stars = stars

    await db.commit()

    result = await db.execute(
        select(Movie)
        .where(Movie.id == movie.id)
        .options(
            joinedload(Movie.certification),
            joinedload(Movie.genres),
            joinedload(Movie.directors),
            joinedload(Movie.stars)
        )
    )
    return result.unique().scalar_one()


async def delete_movie(db: AsyncSession, movie_id: int):
    movie = await get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie is not found")

    result = await db.execute(
        select(PurchasedMovie.id).where(PurchasedMovie.movie_id == movie_id)
    )
    purchase = result.first()
    if purchase:
        raise HTTPException(status_code=400, detail="Cannot delete: movie has been purchased")

    result = await db.execute(
        select(CartItem.id).where(CartItem.movie_id == movie_id)
    )
    in_cart = result.first()
    if in_cart:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete: movie is currently in users' carts."
        )

    await db.delete(movie)
    await db.commit()


async def purchase_movie(
        db: AsyncSession,
        user_id: int,
        movie_id: int,
        payment_id: int
) -> PurchasedMovie:
    purchased_movie = PurchasedMovie(
        user_id=user_id,
        movie_id=movie_id,
        payment_id=payment_id
    )

    db.add(purchased_movie)
    await db.commit()
    await db.refresh(purchased_movie)

    return purchased_movie
