from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.users.auth.schema import (
    TokenPairSchema, LoginSchema, AccessTokenSchema, RefreshTokenSchema,
    PasswordResetConfirmSchema, PasswordResetRequestSchema, LogoutSchema, PasswordChangeSchema)
from src.users.auth.service import (
    authenticate_user, create_refresh_token, get_refresh_token, delete_refresh_token,
    get_password_reset_token, get_user_by_id, update_user_password,
    delete_password_reset_token, get_user_by_email, create_password_reset_token)
from src.users.config.database import get_async_db
from src.users.dependencies import get_current_user
from src.users.models import User
from src.users.service import send_password_reset_email
from src.users.utils.security import create_access_token, decode_token, verify_password, hash_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenPairSchema)
async def login(
        request: LoginSchema,
        db: AsyncSession = Depends(get_async_db)
):
    user = await authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=15)
    )
    refresh_token = await create_refresh_token(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=AccessTokenSchema)
async def refresh_token(
        refresh: RefreshTokenSchema,
        db: AsyncSession = Depends(get_async_db)
):
    stored_token = await get_refresh_token(db, refresh.refresh_token)
    if not stored_token or stored_token.is_expired():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    payload = decode_token(refresh.refresh_token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = await get_user_by_id(db, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    access_token = create_access_token(data={"sub": user_id})
    return {"access_token": access_token}


@router.post("/logout")
async def logout(
        data: LogoutSchema,
        db: AsyncSession = Depends(get_async_db)
):
    deleted = await delete_refresh_token(db, data.refresh_token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Refresh token not found")
    return {"message": "Logged out successfully"}


@router.post("/password/reset")
async def reset_password(
        request: PasswordResetConfirmSchema,
        db: AsyncSession = Depends(get_async_db)
):
    token = await get_password_reset_token(db, request.token)
    if not token or token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await get_user_by_id(db, token.user_id)
    await update_user_password(db, user, request.new_password)
    await delete_password_reset_token(db, token.token)

    return {"message": "Password reset successfully"}


@router.post("/password/forgot")
async def forgot_password(
        request: PasswordResetRequestSchema,
        db: AsyncSession = Depends(get_async_db)
):
    user = await get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = await create_password_reset_token(db, user)
    await send_password_reset_email(user.email, token.token)
    return {"message": "Password reset email sent"}


@router.post("/password/change")
async def change_password(
        request: PasswordChangeSchema,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db)
):
    if not verify_password(request.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")

    new_hashed_password = hash_password(request.new_password)
    current_user.hashed_password = new_hashed_password
    await db.commit()

    return {"message": "Password changed successfully"}
