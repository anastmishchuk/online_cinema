from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


from src.movies.models import Movie, MovieRating
from src.movies.schemas import MovieOut, MovieFilter, LikeResponse, LikeCreate, MovieRatingCreate, MovieRatingRead
from src.movies.crud.movies import create_movie, update_movie, get_movies_filtered, like_or_dislike_movie
from src.movies.schemas import MovieCreate, MovieRead, MovieUpdate
from src.movies.services import add_movie_to_favorites, remove_movie_from_favorites

from src.users.config.database import get_async_db
from src.users.dependencies import get_current_user
from src.users.models import User
from src.users.permissions import is_moderator


router = APIRouter()


@router.get("/", response_model=list[MovieRead])
async def list_movies(
    filters: MovieFilter = Depends(),
    db: AsyncSession = Depends(get_async_db),
):
    movies = await get_movies_filtered(db, filters)
    return movies


@router.get("/{movie_id}", response_model=MovieOut)
async def read_movie(movie_id: int, session: AsyncSession = Depends(get_async_db)):
    result = await session.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    return movie



@router.post("/", response_model=MovieRead)
async def create_movie_moderator(
    movie_in: MovieCreate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator),
):
    return await create_movie(db, movie_in)


@router.put("/{movie_id}", response_model=MovieRead)
async def update_movie_moderator(
    movie_id: int,
    movie_in: MovieUpdate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator),
):
    return await update_movie(db, movie_id, movie_in)


"""
This function will be finished after Payment module
"""

# @router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_movie(
#     movie_id: int,
#     db: AsyncSession = Depends(get_async_db),
#     user: User = Depends(is_moderator),
# ):
#     await delete_movie(db, movie_id)


@router.post("/movies/{movie_id}", response_model=LikeResponse)
async def like_movie(
    movie_id: int,
    like_request: LikeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await like_or_dislike_movie(
        db,
        current_user.id,
        movie_id,
        like_request.liked
    )


@router.post("/movies/{movie_id}/favorite", status_code=204)
async def add_to_favorites(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):

    await add_movie_to_favorites(db, user_id=current_user.id, movie_id=movie_id)
    return

@router.delete("/movies/{movie_id}/favorite", status_code=204)
async def remove_from_favorites(
    movie_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):

    await remove_movie_from_favorites(db, user_id=current_user.id, movie_id=movie_id)
    return


@router.post("/movies/{movie_id}/rate", response_model=MovieRatingRead)
async def rate_movie(
    movie_id: int,
    rating_in: MovieRatingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = select(MovieRating).where(
        MovieRating.user_id == current_user.id,
        MovieRating.movie_id == movie_id
    )
    result = await db.execute(stmt)
    existing_rating = result.scalar_one_or_none()

    if existing_rating:
        existing_rating.rating = rating_in.rating
    else:
        new_rating = MovieRating(
            user_id=current_user.id,
            movie_id=movie_id,
            rating=rating_in.rating
        )
        db.add(new_rating)

    await db.commit()

    return MovieRatingRead(movie_id=movie_id, rating=rating_in.rating)
