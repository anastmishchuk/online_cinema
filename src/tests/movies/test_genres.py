import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.movies.models import Genre
from src.tests.users.conftest import authenticated_client, admin_client, moderator_client


class TestGenreCRUD:

    @pytest.mark.asyncio
    async def test_create_genre_by_admin(self,  admin_client: AsyncClient):
        genre_data = {"name": "Action"}
        response = await admin_client.post(
            "/api/v1/genres/", json=genre_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Action"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_genre_by_moderator(self, moderator_client: AsyncClient):
        genre_data = {"name": "Drama"}
        response = await moderator_client.post(
            "/api/v1/genres/", json=genre_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Drama"
        assert "id" in data

    async def test_create_genre_user(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test creating a genre without proper authentication (should fail)."""
        genre_data = {"name": "Sci-Fi"}

        response = await authenticated_client.post(
            "/api/v1/genres/", json=genre_data
        )

        assert response.status_code == 403

    async def test_update_genre(self, moderator_client: AsyncClient, db_session: AsyncSession):
        """Test updating a genre by admin or moderator."""

        genre_data = {"name": "Drama"}
        response = await moderator_client.post(
            "/api/v1/genres/", json=genre_data
        )
        genre_id = response.json()["id"]

        update_data = {"name": "Thriller"}
        response = await moderator_client.put(
            f"/api/v1/genres/{genre_id}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["id"] == genre_id

        stmt = select(Genre).where(Genre.id == genre_id)
        result = await db_session.execute(stmt)
        genre = result.scalar_one()
        assert genre.name == update_data["name"]

    async def test_delete_genre(self, moderator_client: AsyncClient, db_session: AsyncSession):
        """Test deleting a genre by admin or moderator."""

        genre_data = {"name": "Sci-Fi"}
        response = await moderator_client.post(
            "/api/v1/genres/", json=genre_data
        )
        genre_id = response.json()["id"]

        stmt = select(Genre).where(Genre.id == genre_id)
        result = await db_session.execute(stmt)
        genre = result.scalar_one()
        assert genre.name == genre_data["name"]

        response = await moderator_client.delete(f"/api/v1/genres/{genre_id}")
        assert response.status_code == 204

        stmt = select(Genre).where(Genre.id == genre_id)
        result = await db_session.execute(stmt)
        genre = result.scalar_one_or_none()
        assert genre is None


class TestGenreEndpoints:
    async def test_get_genre_by_id(
            self,
            async_client: AsyncClient,
            db_session: AsyncSession,
            sample_genre: Genre
    ):
        """Test getting a genre by ID."""
        response = await async_client.get(f"/api/v1/genres/{sample_genre.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_genre.name
        assert data["id"] == sample_genre.id
        assert "movie_count" in data
        assert data["movie_count"] == 0

    async def test_list_genres_with_movie_count(self, async_client: AsyncClient, db_session: AsyncSession, sample_movies):
        """Test listing genres with movie count."""

        genres = sample_movies["genres"]

        response = await async_client.get("/api/v1/genres/")
        assert response.status_code == 200
        data = response.json()

        assert len(data) > 0

        for genre in data:
            assert "movie_count" in genre

        drama_genre = next((g for g in data if g["name"] == genres[0].name), None)
        action_genre = next((g for g in data if g["name"] == genres[1].name), None)

        assert drama_genre["movie_count"] == 1
        assert action_genre["movie_count"] == 1
