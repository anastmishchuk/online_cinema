import uuid
import secrets

from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.users import models, schemas
from src.users.config import settings
from src.users.models import UserGroupEnum, ActivationToken, PasswordResetToken, User
from src.users.utils.security import hash_password

ACTIVATION_TOKEN_EXPIRY_HOURS = 24


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user_create: schemas.UserCreateSchema):
    hashed_password = hash_password(user_create.password)
    user = models.User(
        email=user_create.email,
        hashed_password=hashed_password,
        is_active=False,
        group_id=UserGroupEnum.USER.value
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token_str = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=ACTIVATION_TOKEN_EXPIRY_HOURS)
    activation_token = models.ActivationToken(
        user_id=user.id,
        token=token_str,
        expires_at=expires_at
    )
    db.add(activation_token)
    db.commit()
    db.refresh(activation_token)

    user.activation_token = activation_token
    return user


def activate_user(db: Session, token: str):
    token_obj = db.query(models.ActivationToken).filter(models.ActivationToken.token == token).first()
    if not token_obj or token_obj.expires_at < datetime.utcnow():
        return None
    user = db.query(models.User).filter(models.User.id == token_obj.user_id).first()
    if not user:
        return None
    user.is_active = True
    db.delete(token_obj)
    db.commit()
    return user


def regenerate_activation_token(db: Session, user):
    existing_token = db.query(ActivationToken).filter(ActivationToken.user_id == user.id).first()
    if existing_token:
        db.delete(existing_token)
        db.commit()

    token_str = secrets.token_urlsafe(32)
    new_token = ActivationToken(
        user_id=user.id,
        token=token_str,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(new_token)
    db.commit()
    db.refresh(new_token)
    return new_token


def authenticate_user(db: Session, email: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not password.verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


def create_refresh_token(db: Session, user_id: int) -> str:
    token = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=7)

    refresh_token = models.RefreshToken(
        token=token,
        user_id=user_id,
        expires_at=expires_at
    )
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    return token


def get_refresh_token(db: Session, token: str) -> models.RefreshToken | None:
    db_token = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == token,
        models.RefreshToken.expires_at > datetime.utcnow()
    ).first()
    return db_token


def delete_refresh_token(db: Session, token: str):
    db_token = db.query(models.RefreshToken).filter(
        models.RefreshToken.token == token
    ).first()
    if db_token:
        db.delete(db_token)
        db.commit()


def create_password_reset_token(db: Session, user: User) -> PasswordResetToken:
    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    token = PasswordResetToken(token=token_str, user_id=user.id, expires_at=expires_at)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_password_reset_token(db: Session, token_str: str) -> Optional[PasswordResetToken]:
    return db.query(PasswordResetToken).filter_by(token=token_str).first()


def delete_password_reset_token(db: Session, token_str: str) -> None:
    db.query(PasswordResetToken).filter_by(token=token_str).delete()
    db.commit()


def update_user_password(db: Session, user: User, new_password: str):
    user.hashed_password = hash_password(new_password)
    db.commit()
