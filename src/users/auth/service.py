import uuid
import secrets

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.users import models
from src.users.auth.schema import UserCreateSchema
from src.users.config.settings import settings
from src.users.models import UserGroupEnum, ActivationToken, PasswordResetToken, User, RefreshToken
from src.users.utils.security import hash_password, verify_password

ACTIVATION_TOKEN_EXPIRY_HOURS = 24


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()


async def create_user(db: AsyncSession, user_create: UserCreateSchema):
    hashed_password = hash_password(user_create.password)
    user = User(
        email=user_create.email,
        hashed_password=hashed_password,
        is_active=False,
        group_id=UserGroupEnum.USER.value
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token_str = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=ACTIVATION_TOKEN_EXPIRY_HOURS)
    activation_token = models.ActivationToken(
        user_id=user.id,
        token=token_str,
        expires_at=expires_at
    )
    db.add(activation_token)
    await db.commit()
    await db.refresh(activation_token)

    user.activation_token = activation_token
    return user


async def activate_user(db: AsyncSession, token: str):
    result = await db.execute(
        select(ActivationToken).where(ActivationToken.token == token)
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


async def regenerate_activation_token(db: AsyncSession, user: User):
    result = await db.execute(
        select(ActivationToken).where(ActivationToken.user_id == user.id)
    )
    existing_token = result.scalar_one_or_none()
    if existing_token:
        await db.delete(existing_token)

    token_str = secrets.token_urlsafe(32)
    new_token = ActivationToken(
        user_id=user.id,
        token=token_str,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )

    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)

    return new_token


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    user = result.scalar_one_or_none()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def create_refresh_token(db: AsyncSession, user_id: int) -> str:
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=7)

    refresh_token = models.RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(refresh_token)

    await db.commit()
    await db.refresh(refresh_token)

    return token


async def get_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.token == token,
        RefreshToken.expires_at > datetime.utcnow())
    )

    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token: str):
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.token == token)
    )
    db_token = result.scalar_one_or_none()

    if db_token:
        await db.delete(db_token)
        await db.commit()
        return True
    return False


async def create_password_reset_token(db: AsyncSession, user: User) -> PasswordResetToken:
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    token = PasswordResetToken(token=token_str, user_id=user.id, expires_at=expires_at)
    db.add(token)
    await db.commit()
    await db.refresh(token)

    return token


async def get_password_reset_token(db: AsyncSession, token_str: str) -> Optional[PasswordResetToken]:
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token_str)
    )
    return result.scalars().first()


async def delete_password_reset_token(db: AsyncSession, token_str: str) -> None:
    await db.execute(
        delete(PasswordResetToken).where(PasswordResetToken.token == token_str)
    )
    await db.commit()


async def update_user_password(db: AsyncSession, user: User, new_password: str):
    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()
