import uuid
from datetime import datetime

from sqlalchemy import (
    and_,
    Boolean,
    Column,
    DateTime,
    DECIMAL,
    func,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import foreign, relationship

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

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)

    movies = relationship("Movie", secondary=movie_genres, back_populates="genres")


class Star(Base):
    __tablename__ = "stars"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)

    movies = relationship("Movie", secondary=movie_stars, back_populates="stars")


class Director(Base):
    __tablename__ = "directors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, nullable=False)

    movies = relationship("Movie", secondary=movie_directors, back_populates="directors")


class Certification(Base):
    __tablename__ = "certifications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, nullable=False)

    movies = relationship("Movie", back_populates="certification")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    target_type = Column(String, nullable=False)  # "movie" or "comment"
    target_id = Column(Integer, nullable=False)

    is_like = Column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uix_user_target"),
    )

    user = relationship("User", back_populates="likes")
    movie = relationship(
        "Movie",
        back_populates="likes",
        primaryjoin=lambda: and_(
            foreign(Like.target_id) == Movie.id,
            Like.target_type == "movie"
        ),
        viewonly=True,
    )

    comment = relationship(
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

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    year = Column(Integer, nullable=False)
    time = Column(Integer, nullable=False)  # duration in minutes
    imdb = Column(Float, nullable=False)
    votes = Column(Integer, nullable=False)
    meta_score = Column(Float, nullable=True)
    gross = Column(Float, nullable=True)
    description = Column(Text, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=True)
    certification_id = Column(Integer, ForeignKey("certifications.id"), nullable=False)


    certification = relationship("Certification", back_populates="movies")
    genres = relationship("Genre", secondary=movie_genres, back_populates="movies")
    directors = relationship("Director", secondary=movie_directors, back_populates="movies")
    stars = relationship("Star", secondary=movie_stars, back_populates="movies")
    likes = relationship(
        "Like",
        back_populates="movie",
        primaryjoin=and_(
            id == foreign(Like.target_id),
            Like.target_type == "movie"
        )
    )
    ratings = relationship("MovieRating", back_populates="movie")
    favorited_by = relationship(
        "User",
        secondary=favorite_movies,
        back_populates="favorite_movies"
    )


class MovieRating(Base):
    __tablename__ = "movie_ratings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-10 scale

    user = relationship("User", back_populates="movie_ratings")
    movie = relationship("Movie", back_populates="ratings")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="user_movie_unique"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    movie = relationship("Movie")
    parent = relationship("Comment", remote_side=[id], backref="replies")

    likes = relationship(
        "Like",
        back_populates="comment",
        primaryjoin=and_(
            id == foreign(Like.target_id),
            Like.target_type == "comment"
        )
    )


class PurchasedMovie(Base):
    __tablename__ = "purchased_movies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    purchased_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="purchased_movies")
    movie = relationship("Movie")

    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uix_user_movie_purchase"),
    )
