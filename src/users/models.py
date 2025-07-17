from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SqlEnum,
    Text,
)
from sqlalchemy.orm import mapped_column, relationship, Mapped

from src.config.database import Base
from src.movies.schemas import MovieOut
from src.movies.models import favorite_movies, Like, Movie, MovieRating, PurchasedMovie
from src.cart.models import Cart
from src.payment.models import Payment
from src.orders.models import Order, RefundRequest


class UserGroupEnum(str, Enum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[UserGroupEnum] = mapped_column(SqlEnum(UserGroupEnum), unique=True, nullable=False)

    users: Mapped[list["User"]] = relationship("User", back_populates="group")

    def __str__(self) -> str:
        return str(self.name)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_groups.id"), nullable=False)
    group: Mapped[UserGroup] = relationship("UserGroup", back_populates="users", lazy="selectin")

    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False
    )
    activation_token: Mapped["ActivationToken"] = relationship(
        "ActivationToken",
        back_populates="user",
        uselist=False
    )
    password_reset_token: Mapped["PasswordResetToken"] = relationship(
        "PasswordResetToken",
        back_populates="user",
        uselist=False
    )
    refresh_token: Mapped["RefreshToken"] = relationship(
        "RefreshToken",
        back_populates="user"
    )

    likes: Mapped[list["Like"]] = relationship(
        "Like",
        back_populates="user"
    )
    favorite_movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=favorite_movies,
        back_populates="favorited_by"
    )
    movie_ratings: Mapped[list["MovieRating"]] = relationship(
        "MovieRating",
        back_populates="user"
    )
    purchased_movies: Mapped[list["PurchasedMovie"]] = relationship(
        "PurchasedMovie",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    cart: Mapped["Cart"] = relationship(
        "Cart",
        back_populates="user",
        uselist=False
    )
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    refund_requests: Mapped[list["RefundRequest"]] = relationship(
        "RefundRequest",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="user"
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    avatar: Mapped[str] = mapped_column(String(255), nullable=True)
    date_of_birth: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    info: Mapped[str] = mapped_column(Text, nullable=True)

    favorites: Mapped[list[MovieOut]] = []

    user: Mapped["User"] = relationship("User", back_populates="profile")


def __str__(self) -> str:
        if self.first_name or self.last_name:
            return f"{self.first_name or ''} {self.last_name or ''}".strip()
        return "User Profile"


class ActivationToken(Base):
    __tablename__ = "activation_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="activation_token")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="password_reset_token")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="refresh_token")


def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
