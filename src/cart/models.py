from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, UniqueConstraint, func
from sqlalchemy.orm import relationship, mapped_column, Mapped
from typing import TYPE_CHECKING

from src.config.database import Base

if TYPE_CHECKING:
    from src.users.models import User
    from src.movies.models import Movie


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="cart"
    )
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan"
    )

    def __str__(self):
        return f"Cart {self.id} (User ID: {self.user_id})"


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    cart: Mapped["Cart"] = relationship(
        "Cart",
        back_populates="cart_items"
    )
    movie: Mapped["Movie"] = relationship(
        "Movie",
        back_populates="cart_items"
    )

    __table_args__ = (
        UniqueConstraint("cart_id", "movie_id", name="uix_cart_movie"),
    )

    def __str__(self):
        return f"CartItem {self.id} (Movie ID: {self.movie_id})"
