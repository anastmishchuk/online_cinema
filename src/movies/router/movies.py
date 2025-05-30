from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


from src.movies.models import Movie, MovieRating, Comment
from src.movies.schemas import (
    MovieOut,
    MovieFilter,
    LikeRead,
    LikeCreate,
    MovieRatingCreate,
    MovieRatingRead,
    CommentCreate
)
from src.movies.crud.movies import (
    create_movie,
    update_movie,
    get_movies_filtered
)
from src.movies.schemas import MovieCreate, MovieRead, MovieUpdate
from src.movies.services import add_movie_to_favorites, remove_movie_from_favorites, like_or_dislike_comment, \
    like_or_dislike

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


@router.post("/movies/{movie_id}/like", response_model=LikeRead)
async def like_movie(
    movie_id: int,
    like_request: LikeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await like_or_dislike(
        db=db,
        user_id=current_user.id,
        target_type="movie",
        target_id=movie_id,
        is_like=like_request.is_like
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


@router.post("/movies/{movie_id}/comments", status_code=201)
async def add_comment(
    movie_id: int,
    comment_in: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")

    if comment_in.parent_id is not None:
        result = await db.execute(select(Comment).where(Comment.id == comment_in.parent_id))
        parent = result.scalar_one_or_none()
        if parent is None or parent.movie_id != movie_id:
            raise HTTPException(status_code=400, detail="Invalid parent comment")

    new_comment = Comment(
        user_id=current_user.id,
        movie_id=movie_id,
        text=comment_in.text,
        parent_id=comment_in.parent_id
    )

    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)

    return new_comment


@router.post("/comments/{comment_id}/like", response_model=LikeRead)
async def like_comment(
        comment_id: int,
        like_request: LikeCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
):
    return await like_or_dislike(
        db=db,
        user_id=current_user.id,
        target_type="comment",
        target_id=comment_id,
        is_like=like_request.is_like
    )
