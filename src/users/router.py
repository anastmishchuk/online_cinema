from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_async_db
from src.movies.crud.movies import get_movies_filtered
from src.movies.schemas import (
    MovieFilter,
    MovieRead,
    PurchasedMovieOut
)
from src.movies.services import get_user_purchased_movies
from src.users.auth.schema import (
    ActivationRequestSchema,
    ActivationConfirmSchema,
    UserRegisterSchema,
    UserCreateSchema,
)
from src.users.auth.service import (
    activate_user,
    create_user,
    create_profile_for_user,
    get_user_by_email,
    get_user_by_id,
    regenerate_activation_token, get_group_id_by_name,
)
from src.users.dependencies import get_current_user
from src.users.models import User, UserProfile
from src.users.permissions import is_admin
from src.users.schemas import (
    RoleChangeSchema,
    UserReadSchema,
    UserProfileRead,
    UserProfileUpdate
)
from src.users.service import send_activation_email
from src.users.utils.security import hash_password


router = APIRouter()


@router.post("/register", response_model=UserReadSchema)
async def register(
    user_register: UserRegisterSchema,
    db: AsyncSession = Depends(get_async_db)
):
    user = await get_user_by_email(db, user_register.email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user_register.password)
    user_create = UserCreateSchema(
        email=user_register.email,
        hashed_password=hashed_password
    )

    new_user = await create_user(db, user_create)

    await send_activation_email(new_user.email, new_user.activation_token.token)

    return new_user


@router.post("/{user_id}/activate")
async def activate(
        request: ActivationConfirmSchema,
        db: AsyncSession = Depends(get_async_db)
):
    user = await activate_user(db, request.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired activation token")
    return {"message": "User activated successfully"}


@router.post("/resend-activation", status_code=200)
async def resend_activation(
        request: ActivationRequestSchema,
        db: AsyncSession = Depends(get_async_db)
):
    user = await get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_active:
        raise HTTPException(status_code=400, detail="User is already activated")

    new_token = await regenerate_activation_token(db, user)
    await send_activation_email(user.email, new_token.token)
    return {"message": "Activation email resent successfully"}


@router.post("/{user_id}/change-role")
async def change_user_role(
    user_id: int,
    role_data: RoleChangeSchema,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(is_admin)
):
    group_id = await get_group_id_by_name(db, role_data.new_role.value)
    result = await db.execute(
        select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    target_user.group_id = group_id
    await db.commit()
    return {"message": f"User role changed to {role_data.new_role.value}"}


@router.post("/{user_id}/activate")
async def activate_user_account(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(is_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.is_active:
        return {"message": "User account is already active"}

    target_user.is_active = True
    await db.commit()
    return {"message": f"User {target_user.email} activated successfully"}


@router.get("/activate/{token}")
async def activate_via_link(
    token: str,
    db: AsyncSession = Depends(get_async_db)
):
    user = await activate_user(db, token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired activation token")
    return {"message": "User activated successfully"}


@router.get("/{user_id}/profile", response_model=UserProfileRead)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalars().first()
    if profile is None:
        user = await get_user_by_id(db, current_user.id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        profile = await create_profile_for_user(db, user)
        if profile is None:
            raise HTTPException(status_code=500, detail="Could not create profile")

    return profile


@router.put("/{user_id}/profile", response_model=UserProfileRead)
async def update_profile(
    profile_update: UserProfileUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    profile = current_user.profile

    for field, value in profile_update.dict(exclude_unset=True).items():
        setattr(profile, field, value)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return profile


@router.get("/{user_id}/profile/favorites", response_model=List[MovieRead])
async def get_favorites_list(
    filters: MovieFilter = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    favorites = await get_movies_filtered(db, filters, user_id=current_user.id)
    return favorites


@router.get("/{user_id}/profile/purchases", response_model=List[PurchasedMovieOut])
async def get_user_purchases(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    return await get_user_purchased_movies(db, current_user.id)
