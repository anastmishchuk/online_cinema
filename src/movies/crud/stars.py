from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ...movies.models import Star
from ...movies.schemas import StarCreate, StarUpdate


async def get_star_by_id(db: AsyncSession, star_id: int) -> Star | None:
    result = await db.execute(select(Star).where(Star.id == star_id))
    return result.scalar_one_or_none()


async def get_all_stars(db: AsyncSession) -> list[Star]:
    result = await db.execute(select(Star))
    return result.scalars().all()


async def create_star(db: AsyncSession, star_in: StarCreate) -> Star:
    star = Star(**star_in.dict())
    db.add(star)
    await db.commit()
    await db.refresh(star)
    return star


async def update_star(db: AsyncSession, star_id: int, star_in: StarUpdate) -> Star:
    star = await get_star_by_id(db, star_id)
    if not star:
        raise HTTPException(status_code=404, detail="Star is not found")

    if star_in.name is not None:
        star.name = star_in.name

    await db.commit()
    await db.refresh(star)
    return star


async def delete_star(db: AsyncSession, star_id: int) -> None:
    star = await get_star_by_id(db, star_id)
    if not star:
        raise HTTPException(status_code=404, detail="Star is not found")

    await db.delete(star)
    await db.commit()
