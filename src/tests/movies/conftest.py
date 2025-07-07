import uuid
import uuid as uuid_module
import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from src.movies.models import (
    Movie, Genre, Director, Star, Certification,
    Like, MovieRating, Comment, PurchasedMovie, MoviesStarsModel, MoviesDirectorsModel
)


@pytest.fixture
def sample_movie(sample_certification):
    """Create a sample movie."""
    return Movie(
        id=1,
        uuid=uuid_module.uuid4(),
        name="Inception",
        year=2010,
        time=148,
        imdb=8.8,
        votes=2000000,
        meta_score=74.0,
        gross=829895144.0,
        description="A skilled thief is given a chance at redemption.",
        price=Decimal("9.99"),
        certification_id=sample_certification.id,
        certification=sample_certification
    )


@pytest.fixture
def sample_movie_2(sample_certification):
    """Create a second sample movie for testing."""
    return Movie(
        id=2,
        uuid=uuid_module.uuid4(),
        name="The Dark Knight",
        year=2008,
        time=152,
        imdb=9.0,
        votes=2500000,
        meta_score=84.0,
        gross=1004558444.0,
        description="Batman faces the Joker in Gotham City.",
        price=Decimal("12.99"),
        certification_id=sample_certification.id,
        certification=sample_certification
    )


@pytest.fixture
def sample_like(sample_user):
    """Create a sample like."""
    return Like(
        id=1,
        user_id=sample_user.id,
        target_type="movie",
        target_id=1,
        is_like=True
    )


@pytest.fixture
def sample_comment_like(sample_user):
    """Create a sample comment like."""
    return Like(
        id=2,
        user_id=sample_user.id,
        target_type="comment",
        target_id=1,
        is_like=True
    )


@pytest.fixture
def sample_movie_rating(sample_user, sample_movie):
    """Create a sample movie rating."""
    return MovieRating(
        id=1,
        user_id=sample_user.id,
        movie_id=sample_movie.id,
        rating=8
    )


@pytest.fixture
def sample_comment(sample_user, sample_movie):
    """Create a sample comment."""
    return Comment(
        id=1,
        user_id=sample_user.id,
        movie_id=sample_movie.id,
        text="Great movie! Really enjoyed it.",
        parent_id=None,
        created_at=datetime.utcnow()
    )


@pytest.fixture
async def sample_data(db_session):
    """Create sample test data"""
    unique_id = str(uuid.uuid4())[:8]

    cert = Certification(name=f"PG-13-{unique_id}")
    db_session.add(cert)

    action = Genre(name=f"Action-{unique_id}")
    drama = Genre(name=f"Drama-{unique_id}")
    db_session.add_all([action, drama])

    director = Director(name=f"Christopher Nolan-{unique_id}")
    db_session.add(director)

    # Create stars
    star1 = Star(name=f"Leonardo DiCaprio-{unique_id}")
    star2 = Star(name=f"Marion Cotillard-{unique_id}")
    db_session.add_all([star1, star2])

    await db_session.commit()
    await db_session.refresh(cert)
    await db_session.refresh(action)
    await db_session.refresh(drama)
    await db_session.refresh(director)
    await db_session.refresh(star1)
    await db_session.refresh(star2)

    return {
        "certification": cert,
        "genres": [action, drama],
        "director": director,
        "stars": [star1, star2]
    }


@pytest.fixture
async def sample_movies(db_session):
    """Create sample movies for testing"""
    unique_id = str(uuid.uuid4())[:8]

    cert = Certification(name=f"PG-13-{unique_id}")
    db_session.add(cert)
    await db_session.commit()

    action = Genre(name=f"Action-{unique_id}")
    drama = Genre(name=f"Drama-{unique_id}")
    db_session.add_all([action, drama])

    director = Director(name=f"Test Director-{unique_id}")
    star = Star(name=f"Test Star-{unique_id}")
    db_session.add(director)
    db_session.add(star)

    await db_session.commit()

    movies = [
        Movie(
            name=f"Action Movie-{unique_id}",
            year=2023,
            time=120,
            imdb=8.0,
            votes=100000,
            meta_score=75.0,
            description="Action packed movie",
            certification_id=cert.id,
            genres=[action],
            directors=[director],
            stars=[star]
        ),
        Movie(
            name=f"Drama Movie-{unique_id}",
            year=2022,
            time=135,
            imdb=7.5,
            votes=80000,
            meta_score=80.0,
            description="Emotional drama",
            certification_id=cert.id,
            genres=[drama],
            directors=[director],
            stars=[star]
        )
    ]

    db_session.add_all(movies)
    await db_session.commit()

    for movie in movies:
        for director in movie.directors:
            existing_director_relation = await db_session.execute(
                select(MoviesDirectorsModel).filter_by(movie_id=movie.id, director_id=director.id)
            )
            if not existing_director_relation.scalar_one_or_none():
                db_session.add(MoviesDirectorsModel(movie_id=movie.id, director_id=director.id))

        for star in movie.stars:
            existing_star_relation = await db_session.execute(
                select(MoviesStarsModel).filter_by(movie_id=movie.id, star_id=star.id)
            )
            if not existing_star_relation.scalar_one_or_none():
                db_session.add(MoviesStarsModel(movie_id=movie.id, star_id=star.id))

    await db_session.commit()

    for movie in movies:
        print(f"Created movie: {movie.name}")

    return {
        "movies": movies,
        "certification": cert,
        "genres": [action, drama],
        "director": [director],
        "star": [star]
    }