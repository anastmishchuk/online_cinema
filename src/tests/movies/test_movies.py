import pytest
import uuid
from decimal import Decimal
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.movies.models import (
    Movie,
    MovieRating,
    Comment,
    Like,
    PurchasedMovie,
)
from src.movies.crud.movies import (
    get_movies_filtered,
    get_movie,
    get_movies_by_genre_id,
    create_movie,
    update_movie,
    delete_movie,
    purchase_movie
)
from src.movies.schemas import (
    MovieCreate,
    MovieUpdate,
    MovieFilter
)
from src.tests.users.conftest import moderator_client


class TestMovieModels:
    """Test movie model relationships and constraints"""

    async def test_create_movie_with_relationships(self, db_session, sample_movies, moderator_client: AsyncClient):
        """Test creating a movie with all relationships"""
        import uuid

        unique_suffix = str(uuid.uuid4())[:8]
        movie_data = {
            "name": f"New Movie-{unique_suffix}",
            "year": 2024,
            "time": 150,
            "imdb": 9.0,
            "votes": 500000,
            "meta_score": 85.0,
            "gross": 1000000000.0,
            "description": "A brand new movie for testing.",
            "price": "24.99",
            "certification_id": sample_movies["certification"].id,
            "genre_ids": [genre.id for genre in sample_movies["genres"]],
            "director_ids": [director.id for director in sample_movies["directors"]],
            "star_ids": [star.id for star in sample_movies["stars"]]
        }

        response = await moderator_client.post("/api/v1/movies/", json=movie_data)
        assert response.status_code == 201

        created_movie = response.json()
        movie_id = created_movie["id"]

        response = await moderator_client.get(f"/api/v1/movies/{movie_id}")
        assert response.status_code == 200

        movie = response.json()

        assert len(movie["genres"]) == 2
        assert len(movie["directors"]) == 1
        assert len(movie["stars"]) == 1

    async def test_movie_rating_relationship(self, db_session, sample_data, test_user):
        """Test movie rating relationship and constraints"""
        movie = Movie(
            name="Test Movie",
            year=2023,
            time=120,
            imdb=7.5,
            votes=10000,
            description="Test description",
            certification_id=sample_data["certification"].id
        )
        db_session.add(movie)
        await db_session.commit()

        rating = MovieRating(
            user_id=test_user.id,
            movie_id=movie.id,
            rating=9
        )
        db_session.add(rating)
        await db_session.commit()

        duplicate_rating = MovieRating(
            user_id=test_user.id,
            movie_id=movie.id,
            rating=8
        )
        db_session.add(duplicate_rating)

        with pytest.raises(Exception):
            await db_session.commit()

    async def test_like_polymorphic_relationship(self, db_session, sample_data, test_user):
        """Test like system for movies and comments"""
        unique_id = str(uuid.uuid4())[:8]
        movie = Movie(
            name=f"Test Movie-{unique_id}",
            year=2023,
            time=120,
            imdb=7.5,
            votes=10000,
            description="Test description",
            certification_id=sample_data["certification"].id
        )
        db_session.add(movie)
        await db_session.commit()

        movie_like = Like(
            user_id=test_user.id,
            target_type="movie",
            target_id=movie.id,
            is_like=True
        )
        db_session.add(movie_like)

        comment = Comment(
            user_id=test_user.id,
            movie_id=movie.id,
            text="Great movie!"
        )
        db_session.add(comment)
        await db_session.commit()

        comment_like = Like(
            user_id=test_user.id,
            target_type="comment",
            target_id=comment.id,
            is_like=True
        )
        db_session.add(comment_like)
        await db_session.commit()

        result = await db_session.execute(
            select(Movie)
            .options(
                selectinload(Movie.genres),
                selectinload(Movie.directors),
                selectinload(Movie.stars),
                selectinload(Movie.certification),
                selectinload(Movie.likes),
                selectinload(Movie.comments),
            )
            .where(Movie.id == movie.id)
        )
        movie_with_likes = result.scalar_one()
        assert len(movie_with_likes.likes) == 1
        assert movie_with_likes.likes[0].is_like is True


class TestMovieServices:
    """Test movie service functions"""

    async def test_movie_unique_constraint(self, db_session, sample_data):
        """Test movie unique constraint on name, year, time"""
        unique_id = str(uuid.uuid4())[:8]

        movie1 = Movie(
            name=f"Test Movie-{unique_id}",
            year=2023,
            time=120,
            imdb=7.5,
            votes=10000,
            description="Test description",
            certification_id=sample_data["certification"].id
        )

        movie2 = Movie(
            name=f"Test Movie-{unique_id}",
            year=2023,
            time=120,
            imdb=8.0,
            votes=15000,
            description="Different description",
            certification_id=sample_data["certification"].id
        )

        db_session.add(movie1)
        await db_session.commit()

        db_session.add(movie2)

        with pytest.raises(Exception):
            await db_session.commit()

    async def test_get_movies_filtered_basic(self, db_session, sample_movies):
        """Test basic movie filtering"""
        filters = MovieFilter(page=1, page_size=10)
        movies = await get_movies_filtered(db_session, filters)

        print("Movies:", movies)
        print(f"Number of movies: {len(movies)}")

        assert len(movies) == 2
        assert any(movie.name.startswith("Action") for movie in movies)
        assert any(movie.name.startswith("Drama") for movie in movies)

    async def test_get_movies_filtered_by_year(self, db_session, sample_movies):
        """Test filtering movies by year"""
        filters = MovieFilter(year=2023, page=1, page_size=10)
        movies = await get_movies_filtered(db_session, filters)

        assert len(movies) == 1
        assert "Action" in movies[0].name

    async def test_get_movies_filtered_by_imdb_range(self, db_session, sample_movies):
        """Test filtering movies by IMDB rating range"""
        filters = MovieFilter(min_imdb=7.8, max_imdb=8.5, page=1, page_size=10)
        movies = await get_movies_filtered(db_session, filters)

        assert len(movies) == 1
        assert "Action" in movies[0].name

    async def test_get_movies_filtered_search(self, db_session, sample_movies):
        """Test searching movies by name and description"""
        filters = MovieFilter(search="Action", page=1, page_size=10)
        movies = await get_movies_filtered(db_session, filters)

        assert len(movies) == 1
        assert "Action" in movies[0].name

    async def test_get_movies_filtered_search_by_star(self, db_session, sample_movies):
        """Test searching movies by star name"""
        filters = MovieFilter(search="Test Star", page=1, page_size=10)
        movies = await get_movies_filtered(db_session, filters)
        print("Movies:", movies)

        for movie in movies:
            print(f"Stars in {movie.name}: {[star.name for star in movie.stars]}")

        assert len(movies) == 2

        for movie in movies:
            assert any(star.name.startswith("Test Star") for star in movie.stars)

    async def test_get_movies_filtered_sorting(self, db_session, sample_movies):
        """Test sorting movies"""

        filters = MovieFilter(sort="-imdb", page=1, page_size=10)
        movies = await get_movies_filtered(db_session, filters)

        assert movies[0].imdb >= movies[1].imdb
        assert movies[0].name != movies[1].name

        filters = MovieFilter(sort="year", page=1, page_size=10)
        movies = await get_movies_filtered(db_session, filters)

        assert movies[0].year <= movies[1].year
        assert movies[0].name != movies[1].name

    async def test_get_movies_filtered_pagination(self, db_session, sample_movies):
        """Test pagination"""
        filters = MovieFilter(page=1, page_size=1)
        movies = await get_movies_filtered(db_session, filters)

        assert len(movies) == 1

        filters = MovieFilter(page=2, page_size=1)
        movies = await get_movies_filtered(db_session, filters)

        assert len(movies) == 1

    async def test_get_movie_by_id(self, db_session, sample_movies):
        """Test getting a specific movie by ID"""
        movie_id = sample_movies["movies"][0].id
        movie = await get_movie(db_session, movie_id)

        assert movie is not None
        assert movie.name.startswith("Action")

    async def test_get_movie_not_found(self, db_session):
        """Test getting a non-existent movie"""
        movie = await get_movie(db_session, 99999)
        assert movie is None

    async def test_get_movies_by_genre_id(self, db_session, sample_movies):
        """Test getting movies by genre ID"""
        action_genre = sample_movies["genres"][0]
        movies = await get_movies_by_genre_id(db_session, action_genre.id)

        assert len(movies) == 1
        assert "Action" in movies[0].name

    async def test_create_movie_success(self, db_session, sample_movies):
        """Test creating a new movie"""
        movie_data = MovieCreate(
            name="New Movie",
            year=2024,
            time=110,
            imdb=7.0,
            votes=50000,
            meta_score=70.0,
            gross=100000000.0,
            description="A new movie",
            price=Decimal("15.99"),
            certification_id=sample_movies["certification"].id,
            genre_ids=[sample_movies["genres"][0].id],
            director_ids=[sample_movies["director"][0].id],
            star_ids=[sample_movies["star"][0].id]
        )

        created_movie = await create_movie(db_session, movie_data)

        assert created_movie.id is not None
        assert created_movie.name == "New Movie"
        assert created_movie.uuid is not None
        assert len(created_movie.genres) == 1
        assert len(created_movie.directors) == 1
        assert len(created_movie.stars) == 1

    async def test_create_movie_invalid_certification(self, db_session):
        """Test creating movie with invalid certification"""
        movie_data = MovieCreate(
            name="Invalid Movie",
            year=2024,
            time=110,
            price=Decimal("15.99"),
            imdb=7.0,
            votes=50000,
            description="Invalid movie",
            certification_id=99999,
            genre_ids=[],
            director_ids=[],
            star_ids=[]
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_movie(db_session, movie_data)

        assert exc_info.value.status_code == 400
        assert "Certification not found" in str(exc_info.value.detail)

    async def test_update_movie_success(self, db_session, sample_movies):
        """Test updating a movie"""
        movie_id = sample_movies["movies"][0].id
        update_data = MovieUpdate(
            name="Updated Action Movie",
            imdb=8.5,
            genre_ids=[sample_movies["genres"][1].id]
        )

        updated_movie = await update_movie(movie_id, update_data, db_session)

        assert updated_movie.name == "Updated Action Movie"
        assert updated_movie.imdb == 8.5
        assert len(updated_movie.genres) == 1
        assert "Drama" in updated_movie.genres[0].name

    async def test_update_movie_not_found(self, db_session):
        """Test updating a non-existent movie"""
        update_data = MovieUpdate(name="Updated Movie")

        with pytest.raises(HTTPException) as exc_info:
            await update_movie(99999, update_data, db_session)

        assert exc_info.value.status_code == 404
        assert "Movie not found" in str(exc_info.value.detail)

    async def test_delete_movie_success(self, db_session, sample_movies):
        """Test deleting a movie"""
        movie_id = sample_movies["movies"][0].id

        await delete_movie(db_session, movie_id)

        deleted_movie = await get_movie(db_session, movie_id)
        assert deleted_movie is None

    async def test_delete_movie_not_found(self, db_session):
        """Test deleting a non-existent movie"""
        with pytest.raises(HTTPException) as exc_info:
            await delete_movie(db_session, 99999)

        assert exc_info.value.status_code == 404
        assert "Movie is not found" in str(exc_info.value.detail)

    async def test_delete_movie_with_purchases(self, db_session, sample_movies, test_moderator):
        """Test deleting a movie that has been purchased"""
        movie_id = sample_movies["movies"][0].id

        purchase = PurchasedMovie(
            user_id=test_moderator.id,
            movie_id=movie_id
        )
        db_session.add(purchase)
        await db_session.commit()

        purchase_check = await db_session.execute(select(PurchasedMovie).filter_by(movie_id=movie_id))
        assert purchase_check.scalars().first() is not None

        with pytest.raises(HTTPException) as exc_info:
            await delete_movie(db_session, movie_id)

        assert exc_info.value.status_code == 400
        assert "Cannot delete: movie has been purchased" in str(exc_info.value.detail)

    async def test_purchase_movie_success(self, db_session, sample_movies, test_user):
        """Test purchasing a movie"""
        movie_id = sample_movies["movies"][0].id
        payment_id = 123

        purchased_movie = await purchase_movie(
            db_session, test_user.id, movie_id, payment_id
        )

        assert purchased_movie.id is not None
        assert purchased_movie.user_id == test_user.id
        assert purchased_movie.movie_id == movie_id
        assert purchased_movie.payment_id == payment_id
        assert purchased_movie.purchased_at is not None


class TestMovieFilters:
    """Test MovieFilter functionality"""

    def test_movie_filter_defaults(self):
        """Test default values for MovieFilter"""
        filters = MovieFilter()

        assert filters.page == 1
        assert filters.page_size == 10
        assert filters.search is None
        assert filters.year is None
        assert filters.sort is None

    def test_movie_filter_with_values(self):
        """Test MovieFilter with custom values"""
        filters = MovieFilter(
            page=2,
            page_size=5,
            search="test",
            year=2023,
            min_imdb=7.0,
            max_imdb=9.0,
            sort="-imdb"
        )

        assert filters.page == 2
        assert filters.page_size == 5
        assert filters.search == "test"
        assert filters.year == 2023
        assert filters.min_imdb == 7.0
        assert filters.max_imdb == 9.0
        assert filters.sort == "-imdb"
