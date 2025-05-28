from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.database import get_async_db
from src.users.auth.schema import ActivationRequestSchema, UserRegisterSchema, UserCreateSchema, ActivationConfirmSchema
from src.users.auth.service import (
     activate_user, create_user,
     get_user_by_email,regenerate_activation_token)
from src.users.dependencies import get_current_user
from src.users.models import User
from src.users.permissions import is_admin
from src.users.schemas import RoleChangeSchema, UserReadSchema, UserProfileRead, UserProfileUpdate
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


@router.post("/activate")
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


@router.post("/change-role/{user_id}")
async def change_user_role(
    user_id: int,
    role_data: RoleChangeSchema,
    db: AsyncSession = Depends(get_async_db),
    user=Depends(is_admin)
):
    result = await db.execute(
        select(User).where(User.id == user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    target_user.group = role_data.new_role
    await db.commit()
    return {"message": f"User role changed to {role_data.new_role}"}


@router.post("/activate/{user_id}")
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


@router.get("/profile", response_model=UserProfileRead)
async def get_profile(
        current_user: User = Depends(get_current_user)
):
    return current_user.profile


@router.put("/profile", response_model=UserProfileRead)
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


