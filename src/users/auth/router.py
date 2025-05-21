from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.users.auth.schema import (
    TokenPairSchema, LoginSchema, AccessTokenSchema, RefreshTokenSchema,
    PasswordResetConfirmSchema, PasswordResetRequestSchema)
from src.users.auth.service import (
    authenticate_user, create_refresh_token, get_refresh_token, delete_refresh_token,
    get_password_reset_token, get_user_by_id, update_user_password,
    delete_password_reset_token, get_user_by_email, create_password_reset_token)
from src.users.config.database import get_db
from src.users.service import send_password_reset_email
from src.users.utils.security import create_access_token, decode_token


router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenPairSchema)
def login(request: LoginSchema, db: Session = Depends(get_db)):
    user = authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=15)
    )
    refresh_token = create_refresh_token(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=AccessTokenSchema)
def refresh_token(refresh: RefreshTokenSchema, db: Session = Depends(get_db)):
    stored_token = get_refresh_token(db, refresh.refresh_token)
    if not stored_token or stored_token.is_expired():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    payload = decode_token(refresh.refresh_token)
    user_email = payload.get("sub")
    if user_email is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    access_token = create_access_token(data={"sub": user_email})
    return {"access_token": access_token}


@router.post("/logout")
def logout(refresh: RefreshTokenSchema, db: Session = Depends(get_db)):
    deleted = delete_refresh_token(db, refresh.refresh_token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Refresh token not found")
    return {"message": "Logged out successfully"}


@router.post("/password/reset")
def reset_password(request: PasswordResetConfirmSchema, db: Session = Depends(get_db)):
    token = get_password_reset_token(db, request.token)
    if not token or token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = get_user_by_id(db, token.user_id)
    update_user_password(db, user, request.new_password)
    delete_password_reset_token(db, token.token)

    return {"message": "Password reset successfully"}


@router.post("/password/forgot")
def forgot_password(request: PasswordResetRequestSchema, db: Session = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = create_password_reset_token(db, user)
    send_password_reset_email(user.email, token.token)
    return {"message": "Password reset email sent"}
