import uuid
from datetime import datetime

from sqlalchemy import (
    and_,
    Column,
    DateTime,
    DECIMAL,
    func,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import foreign, relationship, mapped_column, Mapped

from src.config.database import Base


movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("director_id", Integer, ForeignKey("directors.id"), primary_key=True),
)

movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("genre_id", Integer, ForeignKey("genres.id"), primary_key=True),
)

movie_stars = Table(
    "movie_stars",
    Base.metadata,
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
    Column("star_id", Integer, ForeignKey("stars.id"), primary_key=True),
)

favorite_movies = Table(
    "favorite_movies",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("movie_id", Integer, ForeignKey("movies.id"), primary_key=True),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=movie_genres,
        back_populates="genres"
    )


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=movie_stars,
        back_populates="stars"
    )


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        secondary=movie_directors,
        back_populates="directors"
    )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie",
        back_populates="certification"
    )


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


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        UniqueConstraint("name", "year", "time", name="uq_movie_name_year_time"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uuid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(nullable=False)
    time: Mapped[int] = mapped_column(nullable=False)  # duration in minutes
    imdb: Mapped[float] = mapped_column(nullable=False)
    votes: Mapped[int] = mapped_column(nullable=False)
    meta_score: Mapped[float] = mapped_column(nullable=True)
    gross: Mapped[float] = mapped_column(nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id"), nullable=False)

    certification: Mapped["Certification"] = relationship(
        "Certification",
        back_populates="movies"
    )
    genres: Mapped[list["Genre"]] = relationship(
        "Genre",
        secondary=movie_genres,
        back_populates="movies"
    )
    directors: Mapped[list["Director"]] = relationship(
        "Director",
        secondary=movie_directors,
        back_populates="movies"
    )
    stars: Mapped[list["Star"]] = relationship(
        "Star",
        secondary=movie_stars,
        back_populates="movies"
    )
    likes: Mapped[list["Like"]] = relationship(
        "Like",
        back_populates="movie",
        primaryjoin=and_(
            id == foreign(Like.target_id),
            Like.target_type == "movie"
        )
    )
    ratings: Mapped[list["MovieRating"]] = relationship(
        "MovieRating",
        back_populates="movie"
    )
    favorited_by: Mapped[list["User"]] = relationship(
        "User",
        secondary=favorite_movies,
        back_populates="favorite_movies"
    )
    order_items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="movie"
    )


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


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    parent_id: Mapped[int] = mapped_column(ForeignKey("comments.id"), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    user: Mapped["User"] = relationship("User")
    movie: Mapped["Movie"] = relationship("Movie")
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
        )
    )


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

    user: Mapped["User"] = relationship("User", back_populates="purchased_movies")
    movie: Mapped["Movie"] = relationship("Movie")


__table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uix_user_movie_purchase"),
    )
