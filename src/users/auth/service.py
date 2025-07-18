import uuid
import secrets
import jwt

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.settings import settings
from .. import models
from ..schema import UserCreateSchema
from ..models import (
    ActivationToken,
    PasswordResetToken,
    User,
    RefreshToken,
    UserGroup,
    UserProfile
)
from ..utils.security import hash_password, verify_password


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.profile),
            selectinload(User.group)
        )
        .where(User.id == user_id)
    )
    return result.scalars().first()


async def get_group_id_by_name(db: AsyncSession, group_name: str) -> int:
    result = await db.execute(
        select(UserGroup).where(UserGroup.name == group_name)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise Exception(f"Group '{group_name}' not found")
    return group.id


async def create_user(db: AsyncSession, user_create: UserCreateSchema):
    group_id = await get_group_id_by_name(db, user_create.group.value)
    user = User(
        email=user_create.email,
        hashed_password=user_create.hashed_password,
        is_active=False,
        group_id=group_id
    )
    db.add(user)
    await db.flush()

    user_profile = UserProfile(
        user_id=user.id
    )
    db.add(user_profile)

    token_str = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(
        hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS
    )
    activation_token = models.ActivationToken(
        user_id=user.id,
        token=token_str,
        expires_at=expires_at
    )
    db.add(activation_token)
    await db.commit()
    await db.refresh(user)

    result = await db.execute(
        select(User)
        .options(selectinload(User.group))
        .where(User.id == user.id)
    )
    user_with_group = result.scalars().first()

    user_with_group.activation_token = activation_token
    return user_with_group


async def activate_user(db: AsyncSession, token: str):
    result = await db.execute(
        select(ActivationToken)
        .where(ActivationToken.token == token)
    )
    token_obj = result.scalar_one_or_none()
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        return None

    result = await db.execute(
        select(User).where(User.id == token_obj.user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return None

    user.is_active = True
    await db.delete(token_obj)
    await db.commit()

    return user


async def regenerate_activation_token(
        db: AsyncSession,
        user: User
):
    result = await db.execute(
        select(ActivationToken)
        .where(ActivationToken.user_id == user.id)
    )
    existing_token = result.scalar_one_or_none()
    if existing_token:
        await db.delete(existing_token)
        await db.flush()

    token_str = secrets.token_urlsafe(32)
    new_token = ActivationToken(
        user_id=user.id,
        token=token_str,
        expires_at=datetime.utcnow() + timedelta(
            hours=settings.ACTIVATION_TOKEN_EXPIRE_HOURS
        )
    )
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)

    return new_token


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.unique().scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def create_refresh_token(db: AsyncSession, user_id: int) -> str:
    to_encode = {"sub": str(user_id)}
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expires_at})

    refresh_token = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

    token = models.RefreshToken(
        token=refresh_token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(token)

    await db.commit()
    await db.refresh(token)

    return refresh_token


async def get_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.token == token,
        RefreshToken.expires_at > datetime.utcnow())
    )

    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token: str):
    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token == token)
    )
    db_token = result.scalar_one_or_none()

    if db_token:
        await db.delete(db_token)
        await db.commit()
        return True
    return False


async def create_password_reset_token(db: AsyncSession, user: User) -> PasswordResetToken:
    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
    )
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(
        hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
    )
    token = PasswordResetToken(token=token_str, user_id=user.id, expires_at=expires_at)
    db.add(token)
    await db.commit()
    await db.refresh(token)

    return token


async def get_password_reset_token(db: AsyncSession, token_str: str) -> Optional[PasswordResetToken]:
    result = await db.execute(
        select(PasswordResetToken)
        .where(PasswordResetToken.token == token_str,
               PasswordResetToken.expires_at > datetime.utcnow())
    )
    return result.scalars().first()


async def delete_password_reset_token(db: AsyncSession, token_str: str) -> None:
    await db.execute(
        delete(PasswordResetToken)
        .where(PasswordResetToken.token == token_str)
    )
    await db.commit()


async def update_user_password(db: AsyncSession, user: User, new_password: str):
    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()


async def create_profile_for_user(db: AsyncSession, user: User) -> UserProfile:
    profile = UserProfile(user_id=user.id)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
