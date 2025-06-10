from datetime import datetime
from enum import Enum
from typing import List

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SqlEnum,
    Text,
)
from sqlalchemy.orm import relationship

from src.config.database import Base
from src.movies.schemas import MovieOut
from src.movies.models import favorite_movies



class UserGroupEnum(str, Enum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class UserGroup(Base):
    __tablename__ = "user_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(SqlEnum(UserGroupEnum), unique=True, nullable=False)

    users = relationship("User", back_populates="group")

    def __str__(self) -> str:
        return str(self.name)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group_id = Column(Integer, ForeignKey("user_groups.id"), nullable=False)
    group = relationship("UserGroup", back_populates="users", lazy="selectin")

    profile = relationship("UserProfile", back_populates="user", uselist=False)
    activation_token = relationship("ActivationToken", back_populates="user", uselist=False)
    password_reset_token = relationship("PasswordResetToken", back_populates="user", uselist=False)
    refresh_tokens = relationship("RefreshToken", back_populates="user")

    likes = relationship("Like", back_populates="user")
    favorite_movies = relationship("Movie", secondary=favorite_movies, back_populates="favorited_by")
    movie_ratings = relationship("MovieRating", back_populates="user")
    purchased_movies = relationship("PurchasedMovie", back_populates="user", cascade="all, delete-orphan")
    cart = relationship("Cart", back_populates="user", uselist=False)
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    refund_requests = relationship("RefundRequest", back_populates="user", cascade="all, delete-orphan")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar = Column(String(255), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    info = Column(Text, nullable=True)

    favorites: List[MovieOut] = []

    user = relationship("User", back_populates="profile")

    def __str__(self) -> str:
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return "User Profile"


class ActivationToken(Base):
    __tablename__ = "activation_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="activation_token")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="password_reset_token")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
