import uuid as uuid_module
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    and_,
    Column,
    DateTime,
    DECIMAL,
    func,
    ForeignKey,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import foreign, relationship, mapped_column, Mapped
from typing import TYPE_CHECKING

from ..config.database import Base

if TYPE_CHECKING:
    from ..users.models import User
    from ..cart.models import CartItem
    from ..orders.models import OrderItem
    from ..payment.models import Payment


MoviesDirectorsModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "director_id",
        ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)

MoviesGenresModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)

MoviesStarsModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "star_id",
        ForeignKey("stars.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)

FavoriteMoviesModel = Table(
    "favorite_movies",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    extend_existing=True
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesGenresModel,
        back_populates="genres"
    )

    def __str__(self):
        return f"{self.name}"


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesStarsModel,
        back_populates="stars"
    )

    def __str__(self):
        return f"{self.name}"


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=MoviesDirectorsModel,
        back_populates="directors"
    )

    def __str__(self):
        return f"{self.name}"


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        back_populates="certification"
    )

    def __str__(self):
        return f"{self.name}"


class Like(Base):
    __tablename__ = "likes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    target_type: Mapped[str] = mapped_column(nullable=False)  # "movie" or "comment"
    target_id: Mapped[int] = mapped_column(nullable=False)

    is_like: Mapped[bool] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uix_user_target"),
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="likes"
    )
    movie: Mapped["Movie"] = relationship(
        "Movie",
        back_populates="likes",
        primaryjoin=lambda: and_(
            foreign(Like.target_id) == Movie.id,
            Like.target_type == "movie"
        ),
        viewonly=True,
    )
    comment: Mapped["Comment"] = relationship(
        "Comment",
        back_populates="likes",
        primaryjoin=lambda: and_(
            foreign(Like.target_id) == Comment.id,
            Like.target_type == "comment"
        ),
        viewonly=True,
    )

    def __str__(self):
        return f"{self.target_type} {self.target_id} ({self.is_like})"


class MovieRating(Base):
    __tablename__ = "movie_ratings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    rating: Mapped[int] = mapped_column(nullable=False)  # 1-10 scale

    user: Mapped["User"] = relationship("User", back_populates="movie_ratings")
    movie: Mapped["Movie"] = relationship("Movie", back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="user_movie_unique"),
    )

    def __str__(self):
        return f"{self.rating}"


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("comments.id"), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="comments"
    )
    movie: Mapped["Movie"] = relationship(
        "Movie",
        back_populates="comments"
    )
    parent: Mapped["Comment"] = relationship(
        "Comment",
        remote_side=[id],
        backref="replies"
    )
    likes: Mapped[list["Like"]] = relationship(
        "Like",
        back_populates="comment",
        primaryjoin=and_(
            id == foreign(Like.target_id),
            Like.target_type == "comment"
        ),
        overlaps="likes"
    )

    def __str__(self):
        return f"{self.text}"


class PurchasedMovie(Base):
    __tablename__ = "purchased_movies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="purchased_movies"
    )
    movie: Mapped["Movie"] = relationship(
        "Movie",
        back_populates="purchased_movies"
    )
    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="purchased_movies"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uix_user_movie_purchase"),
    )

    def __str__(self):
        return f"PurchasedMovie {self.id} - User: {self.user_id}, Movie: {self.movie_id}, Payment: {self.payment_id}"


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="uq_movie_name_year_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uuid: Mapped[uuid_module.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid_module.uuid4,
        unique=True,
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)  # duration in minutes
    imdb: Mapped[float] = mapped_column(nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[float] = mapped_column(nullable=True)
    gross: Mapped[float] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)

    certification: Mapped["Certification"] = relationship(
        "Certification",
        back_populates="movies"
    )
    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary=MoviesGenresModel,
        back_populates="movies"
    )
    directors: Mapped[list["Director"]] = relationship(
        "Director",
        secondary=MoviesDirectorsModel,
        back_populates="movies"
    )
    stars: Mapped[list["Star"]] = relationship(
        "Star",
        secondary=MoviesStarsModel,
        back_populates="movies"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment",
        back_populates="movie"
    )
    likes: Mapped[list["Like"]] = relationship(
        "Like",
        back_populates="movie",
        primaryjoin=and_(
            id == foreign(Like.target_id),
            Like.target_type == "movie"
        ),
        overlaps="likes",
    )
    ratings: Mapped[list["MovieRating"]] = relationship(
        "MovieRating",
        back_populates="movie"
    )
    favorited_by: Mapped[list["User"]] = relationship(
        "User",
        secondary=FavoriteMoviesModel,
        back_populates="favorite_movies"
    )
    purchased_movies: Mapped[list["PurchasedMovie"]] = relationship(
        "PurchasedMovie",
        back_populates="movie"
    )
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="movie"
    )
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="movie"
    )

    def __str__(self):
        return f"{self.name}"
