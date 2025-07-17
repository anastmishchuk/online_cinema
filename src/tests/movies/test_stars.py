from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from src.movies.models import Star
from src.tests.conftest import (
    authenticated_client,
    admin_client,
    moderator_client
)


class TestStarCRUD:
    async def test_create_star_by_admin(self,  admin_client: AsyncClient):
        star_data = {"name": "Tom Cruise"}
        response = await admin_client.post(
            "/api/v1/stars/", json=star_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Tom Cruise"
        assert "id" in data

    async def test_create_star_by_moderator(self, moderator_client: AsyncClient):
        star_data = {"name": "Jennifer Lawrence"}
        response = await moderator_client.post(
            "/api/v1/stars/", json=star_data
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Jennifer Lawrence"
        assert "id" in data

    async def test_create_genre_user(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession
    ):
        """Test creating a genre without proper authentication (should fail)."""
        star_data = {"name": "Al Pacino"}

        response = await authenticated_client.post(
            "/api/v1/stars/", json=star_data
        )

        assert response.status_code == 403

    async def test_update_star(
            self,
            moderator_client: AsyncClient,
            db_session: AsyncSession
    ):
        """Test updating a star by admin or moderator."""
        star_data = {"name": "Jennifer Lawrence"}
        response = await moderator_client.post(
            "/api/v1/stars/", json=star_data
        )
        star_id = response.json()["id"]

        update_data = {"name": "Jennifer Aniston"}
        response = await moderator_client.put(
            f"/api/v1/stars/{star_id}", json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["id"] == star_id

        stmt = select(Star).where(Star.id == star_id)
        result = await db_session.execute(stmt)
        star = result.scalar_one()
        assert star.name == update_data["name"]

    async def test_delete_star(
            self,
            moderator_client: AsyncClient,
            db_session: AsyncSession
    ):
        """Test deleting a star by admin or moderator."""
        star_data = {"name": "Tom Cruise"}
        response = await moderator_client.post(
            "/api/v1/stars/", json=star_data
        )
        star_id = response.json()["id"]

        stmt = select(Star).where(Star.id == star_id)
        result = await db_session.execute(stmt)
        star = result.scalar_one()
        assert star.name == star_data["name"]

        response = await moderator_client.delete(f"/api/v1/stars/{star_id}")
        assert response.status_code == 204

        stmt = select(Star).where(Star.id == star_id)
        result = await db_session.execute(stmt)
        star = result.scalar_one_or_none()
        assert star is None


class TestGenreEndpoints:
    async def test_get_star_by_id(
            self,
            async_client: AsyncClient,
            db_session: AsyncSession,
            sample_star: Star
    ):
        """Test getting a star by ID."""
        response = await async_client.get(f"/api/v1/stars/{sample_star.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_star.name
        assert data["id"] == sample_star.id

    async def test_list_stars(
            self,
            async_client: AsyncClient,
            db_session: AsyncSession,
            sample_movies: dict
    ):
        """Test listing genres with movie count."""
        response = await async_client.get("/api/v1/stars/")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        star_data = data[0]
        assert "id" in star_data
        assert "name" in star_data
        assert star_data["name"].startswith("Test Star")
