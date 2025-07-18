import uuid
import pytest
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from movies.models import (
    Movie,
    Genre,
    Director,
    Star,
    Certification,
    MoviesStarsModel,
    MoviesDirectorsModel
)


@pytest.fixture
async def sample_data(db_session: AsyncSession):
    """Create sample test data"""
    unique_id = str(uuid.uuid4())[:8]

    cert = Certification(name=f"PG-13-{unique_id}")
    db_session.add(cert)

    action = Genre(name=f"Action-{unique_id}")
    drama = Genre(name=f"Drama-{unique_id}")
    db_session.add_all([action, drama])

    director = Director(name=f"Christopher Nolan-{unique_id}")
    db_session.add(director)

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
async def sample_movies(db_session: AsyncSession):
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
            price=Decimal("9.99"),
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
            price=Decimal("10.99"),
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
        "directors": [director],
        "stars": [star]
    }


@pytest.fixture
async def sample_genre(db_session: AsyncSession) -> Genre:
    """Create a sample genre for testing."""

    genre = Genre(name="Comedy")
    db_session.add(genre)
    await db_session.commit()
    await db_session.refresh(genre)
    return genre


@pytest.fixture
async def sample_star(db_session: AsyncSession) -> Star:
    """Create a sample star for testing."""

    star = Star(name="Leonardo DiCaprio")
    db_session.add(star)
    await db_session.commit()
    await db_session.refresh(star)
    return star
