from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.users import schemas, service
from src.users.config.database import get_db
from src.users.utils.security import create_access_token, decode_token
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=schemas.TokenPairSchema)
def login(request: schemas.LoginSchema, db: Session = Depends(get_db)):
    user = service.authenticate_user(db, request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=15)
    )
    refresh_token = service.create_refresh_token(db, user.id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=schemas.AccessTokenSchema)
def refresh_token(refresh: schemas.RefreshTokenSchema, db: Session = Depends(get_db)):
    stored_token = service.get_refresh_token(db, refresh.refresh_token)
    if not stored_token or stored_token.is_expired():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    payload = decode_token(refresh.refresh_token)
    user_email = payload.get("sub")
    if user_email is None:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    access_token = create_access_token(data={"sub": user_email})
    return {"access_token": access_token}


@router.post("/logout")
def logout(refresh: schemas.RefreshTokenSchema, db: Session = Depends(get_db)):
    deleted = service.delete_refresh_token(db, refresh.refresh_token)
    if not deleted:
        raise HTTPException(status_code=404, detail="Refresh token not found")
    return {"message": "Logged out successfully"}


@router.post("/password/reset")
def reset_password(request: schemas.PasswordResetConfirmSchema, db: Session = Depends(get_db)):
    token = service.get_password_reset_token(db, request.token)
    if not token or token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = service.get_user_by_id(db, token.user_id)
    service.update_user_password(db, user, request.new_password)
    service.delete_password_reset_token(db, token.token)

    return {"message": "Password reset successfully"}


@router.post("/password/forgot")
def forgot_password(request: schemas.PasswordResetRequestSchema, db: Session = Depends(get_db)):
    user = service.get_user_by_email(db, request.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = service.create_password_reset_token(db, user)
    service.send_password_reset_email(user.email, token.token)
    return {"message": "Password reset email sent"}
