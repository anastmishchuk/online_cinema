from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.movies.crud.movies import get_movies_by_genre_id
from src.config.database import get_async_db
from src.movies.models import MoviesGenresModel
from src.users.models import User
from src.users.permissions import is_moderator

from src.movies.schemas import GenreCreate, GenreUpdate, GenreRead, MovieRead
from src.movies.crud.genres import (
    get_genre_by_id,
    get_genres_with_movie_count,
    create_genre,
    update_genre,
    delete_genre
)


router = APIRouter()


@router.get("/", response_model=List[GenreRead])
async def list_genres_with_movie_count(
    db: AsyncSession = Depends(get_async_db),
):
    return await get_genres_with_movie_count(db)


@router.get("/{genre_id}", response_model=GenreRead)
async def get_genre(
    genre_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    genre = await get_genre_by_id(db, genre_id)
    if not genre:
        raise HTTPException(status_code=404, detail="Genre not found")
    return genre


@router.get("/{genre_id}/movies", response_model=List[MovieRead])
async def list_movies_for_genre(
    genre_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    return await get_movies_by_genre_id(db, genre_id)


@router.post("/", response_model=GenreRead, status_code=status.HTTP_201_CREATED)
async def create_genre_view(
    genre_in: GenreCreate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator)
):
    return await create_genre(db, genre_in)


@router.put("/{genre_id}", response_model=GenreRead)
async def update_genre_view(
    genre_id: int,
    genre_in: GenreUpdate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator)
):
    genre = await update_genre(db, genre_id, genre_in)

    result = await db.execute(
        select(func.count(MoviesGenresModel.c.movie_id))
        .where(MoviesGenresModel.c.genre_id == genre.id)
    )
    movie_count = result.scalar_one()

    return {
        "id": genre.id,
        "name": genre.name,
        "movie_count": movie_count
    }


@router.delete("/{genre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_genre_view(
    genre_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator)
):
    await delete_genre(db, genre_id)
