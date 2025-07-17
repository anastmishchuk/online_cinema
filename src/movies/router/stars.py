from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ...config.database import get_async_db
from ...users.models import User
from ...users.permissions import is_moderator
from ...movies.schemas import StarCreate, StarUpdate, StarRead
from ...movies.crud.stars import (
    create_star,
    get_star_by_id,
    get_all_stars,
    update_star,
    delete_star,
)


router = APIRouter()


@router.get("/", response_model=List[StarRead])
async def list_stars(
    db: AsyncSession = Depends(get_async_db),
):
    return await get_all_stars(db)


@router.get("/{star_id}", response_model=StarRead)
async def get_star(
    star_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    star = await get_star_by_id(db, star_id)
    if not star:
        raise HTTPException(status_code=404, detail="Star is not found")
    return star


@router.post("/", response_model=StarRead, status_code=status.HTTP_201_CREATED)
async def create_star_view(
    star_in: StarCreate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator)
):
    return await create_star(db, star_in)


@router.put("/{star_id}", response_model=StarRead)
async def update_star_view(
    star_id: int,
    star_in: StarUpdate,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator)
):
    return await update_star(db, star_id, star_in)


@router.delete("/{star_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_star_view(
    star_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: User = Depends(is_moderator)
):
    await delete_star(db, star_id)
