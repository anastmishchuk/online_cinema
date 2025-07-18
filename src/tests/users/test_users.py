from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from users.models import User, UserGroupEnum


class TestUserRegistrationAndActivation:
    """Test user registration and activation endpoints."""

    async def test_register_user(
            self,
            async_client: AsyncClient,
            valid_user_data: dict,
            create_user_groups: dict
    ):
        """Test user registration."""
        print(f"create_user_groups result: {create_user_groups}")
        with patch("users.router.send_activation_email") as mock_send_email:
            mock_send_email.return_value = None
            response = await async_client.post("/api/v1/users/register", json=valid_user_data)
            assert response.status_code == 201
            data = response.json()
            assert data["email"] == valid_user_data["email"]
            assert data["group"] == "USER"
            assert data["is_active"] is False
            assert "id" in data
            assert "created_at" in data

            assert "password" not in data
            assert "hashed_password" not in data
            assert "activation_token" not in data
            mock_send_email.assert_called_once()

    async def test_register_duplicate_email(
            self,
            async_client: AsyncClient,
            test_user: User,
            valid_user_data: dict
    ):
        """Test registration with already registered email."""
        duplicate_data = valid_user_data.copy()
        duplicate_data["email"] = test_user.email

        response = await async_client.post("/api/v1/users/register", json=duplicate_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    async def test_register_invalid_data(
            self,
            async_client: AsyncClient,
            invalid_user_data: dict
    ):
        """Test registration with invalid data."""
        response = await async_client.post("/api/v1/users/register", json=invalid_user_data)
        assert response.status_code == 422

    async def test_activate_user_with_token(
            self,
            async_client: AsyncClient,
            inactive_user_with_token: User
    ):
        """Test user activation via token."""
        activation_data = {"token": inactive_user_with_token.activation_token.token}
        response = await async_client.post("/api/v1/users/activate", json=activation_data)
        assert response.status_code == 200
        assert "User activated successfully" in response.json()["message"]

    async def test_activate_user_with_invalid_token(
            self,
            async_client: AsyncClient
    ):
        """Test user activation with invalid token."""
        activation_data = {"token": "invalid_token"}
        response = await async_client.post("/api/v1/users/activate", json=activation_data)
        assert response.status_code == 400
        assert "Invalid or expired activation token" in response.json()["detail"]

    async def test_activate_via_link(
            self,
            async_client: AsyncClient,
            inactive_user_with_token: User
    ):
        """Test user activation via GET link."""
        token = inactive_user_with_token.activation_token.token
        response = await async_client.get(f"/api/v1/users/activate/{token}")
        assert response.status_code == 200
        assert "User activated successfully" in response.json()["message"]

    async def test_activate_via_link_invalid_token(
            self,
            async_client: AsyncClient
    ):
        """Test user activation via GET link with invalid token."""
        response = await async_client.get("/api/v1/users/activate/invalid_token")
        assert response.status_code == 400
        assert "Invalid or expired activation token" in response.json()["detail"]

    async def test_resend_activation_email(
            self,
            async_client: AsyncClient,
            inactive_user: User
    ):
        """Test resending activation email."""
        with patch("users.router.send_activation_email") as mock_send_email:
            mock_send_email.return_value = None
            request_data = {"email": inactive_user.email}
            response = await async_client.post("/api/v1/users/resend-activation", json=request_data)
            assert response.status_code == 200
            assert "Activation email resent successfully" in response.json()["message"]
            mock_send_email.assert_called_once()

    async def test_resend_activation_email_user_not_found(
            self,
            async_client: AsyncClient
    ):
        """Test resending activation email for non-existent user."""
        request_data = {"email": "nonexistent@example.com"}
        response = await async_client.post("/api/v1/users/resend-activation", json=request_data)
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    async def test_resend_activation_email_already_active(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test resending activation email for already active user."""
        request_data = {"email": test_user.email}
        response = await async_client.post("/api/v1/users/resend-activation", json=request_data)
        assert response.status_code == 400
        assert "User is already activated" in response.json()["detail"]


class TestUserProfileEndpoints:
    """Test user profile-related endpoints."""

    async def test_get_current_user_profile(
            self,
            authenticated_client: AsyncClient,
            test_user_with_profile: User
    ):
        """Test getting current user profile."""
        response = await authenticated_client.get("/api/v1/users/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == test_user_with_profile.profile.first_name
        assert data["last_name"] == test_user_with_profile.profile.last_name

    async def test_get_profile_creates_if_not_exists(
            self,
            authenticated_client: AsyncClient,
            test_user: User
    ):
        """Test getting profile creates one if it doesn't exist."""
        response = await authenticated_client.get("/api/v1/users/profile")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data

    async def test_get_profile_unauthorized(
            self,
            async_client: AsyncClient
    ):
        """Test getting profile without authentication."""
        response = await async_client.get("/api/v1/users/profile")
        assert response.status_code == 401

    async def test_update_user_profile(
            self,
            authenticated_client: AsyncClient,
            test_user_with_profile: User
    ):
        """Test updating user profile."""
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "info": "Updated info"
        }
        response = await authenticated_client.put("/api/v1/users/profile", json=update_data)
        print(response.json())
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["last_name"] == "Name"
        assert data["info"] == "Updated info"

    async def test_update_profile_unauthorized(
            self,
            async_client: AsyncClient
    ):
        """Test updating profile without authentication."""
        update_data = {"first_name": "Updated"}
        response = await async_client.put("/api/v1/users/profile", json=update_data)
        assert response.status_code == 401

    async def test_get_user_favorites(
            self,
            authenticated_client: AsyncClient,
            test_user_with_favorites: User
    ):
        """Test getting current user's favorite movies."""
        response = await authenticated_client.get("/api/v1/users/profile/favorites")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

        for favorite in data:
            assert "id" in favorite
            assert "name" in favorite
            assert "year" in favorite
            assert "price" in favorite
            assert "imdb" in favorite
            assert "time" in favorite

        names = [movie["name"] for movie in data]
        assert any("Action Hero Returns" in name for name in names)
        assert any("Space Warriors" in name for name in names)
        assert any("Classic Drama" in name for name in names)

    async def test_get_user_favorites_with_filters(
            self,
            authenticated_client: AsyncClient,
            test_user_with_favorites: User
    ):
        """Test getting user's favorites with filters."""
        params = {"year": 2020}
        response = await authenticated_client.get("/api/v1/users/profile/favorites", params=params)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        assert len(data) == 2

        for movie in data:
            assert movie["year"] == 2020

    async def test_get_user_purchases(
            self,
            authenticated_client: AsyncClient,
            test_user_with_purchases: User,
            db_session: AsyncSession
    ):
        """Test getting current user's purchased movies."""
        response = await authenticated_client.get("/api/v1/users/profile/purchases")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        for purchase in data:
            assert "id" in purchase
            assert "name" in purchase
            assert "purchased_at" in purchase

        names = [movie["name"] for movie in data]
        assert "Purchased Movie 1" in names
        assert "Purchased Movie 2" in names

    async def test_get_user_favorites_empty(
            self,
            authenticated_client: AsyncClient,
            test_user_no_favorites: User
    ):
        """Test getting favorites when user has none."""
        response = await authenticated_client.get("/api/v1/users/profile/favorites")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_user_purchases_empty(
            self,
            authenticated_client: AsyncClient,
            test_user_no_purchases: User
    ):
        """Test getting purchases when user has none."""
        response = await authenticated_client.get("/api/v1/users/profile/purchases")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    async def test_get_purchases_unauthorized(
            self,
            async_client: AsyncClient
    ):
        """Test getting purchases without authentication."""
        response = await async_client.get("/api/v1/users/profile/purchases")
        assert response.status_code == 401


class TestAdminEndpoints:
    """Test admin-only endpoints."""

    async def test_admin_activate_user(
            self,
            admin_client: AsyncClient,
            inactive_user: User
    ):
        """Test admin activating a user."""
        response = await admin_client.post(f"/api/v1/users/{inactive_user.id}/admin-activate")
        assert response.status_code == 200
        assert "activated successfully" in response.json()["message"]

    async def test_admin_activate_already_active_user(
            self,
            admin_client: AsyncClient,
            test_user: User
    ):
        """Test admin activating an already active user."""
        response = await admin_client.post(f"/api/v1/users/{test_user.id}/admin-activate")
        assert response.status_code == 200
        assert "already active" in response.json()["message"]

    async def test_admin_activate_non_existent_user(
            self,
            admin_client: AsyncClient
    ):
        """Test admin activating a non-existent user."""
        response = await admin_client.post("/api/v1/users/99999/admin-activate")
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    async def test_admin_activate_unauthorized(
            self,
            authenticated_client: AsyncClient,
            inactive_user: User
    ):
        """Test non-admin trying to activate user."""
        response = await authenticated_client.post(f"/api/v1/users/{inactive_user.id}/admin-activate")
        assert response.status_code == 403

    async def test_change_user_role(
            self,
            admin_client: AsyncClient,
            test_user: User
    ):
        """Test changing user role."""
        role_data = {"new_role": UserGroupEnum.ADMIN}
        response = await admin_client.post(f"/api/v1/users/{test_user.id}/change-role", json=role_data)
        assert response.status_code == 200
        assert "role changed" in response.json()["message"]

    async def test_change_user_role_unauthorized(
            self,
            authenticated_client: AsyncClient,
            test_user: User
    ):
        """Test changing user role without admin privileges."""
        role_data = {"new_role": UserGroupEnum.ADMIN}
        response = await authenticated_client.post(f"/api/v1/users/{test_user.id}/change-role", json=role_data)
        assert response.status_code == 403

    async def test_change_role_non_existent_user(
            self,
            admin_client: AsyncClient
    ):
        """Test changing role for non-existent user."""
        role_data = {"new_role": UserGroupEnum.ADMIN}
        response = await admin_client.post("/api/v1/users/99999/change-role", json=role_data)
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]

    async def test_admin_get_user_profile(
            self,
            admin_client: AsyncClient,
            test_user_with_profile: User
    ):
        """Test admin getting any user's profile."""
        response = await admin_client.get(f"/api/v1/users/{test_user_with_profile.id}/profile")
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == test_user_with_profile.profile.first_name

    async def test_admin_get_user_profile_unauthorized(
            self,
            authenticated_client: AsyncClient,
            test_user: User
    ):
        """Test non-admin trying to get user profile."""
        response = await authenticated_client.get(f"/api/v1/users/{test_user.id}/profile")
        assert response.status_code == 403

    async def test_admin_get_user_favorites(
            self,
            admin_client: AsyncClient,
            test_user_with_favorites: User
    ):
        """Test admin getting any user's favorites."""
        response = await admin_client.get(f"/api/v1/users/{test_user_with_favorites.id}/profile/favorites")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_admin_get_user_favorites_unauthorized(
            self,
            authenticated_client: AsyncClient,
            test_user: User
    ):
        """Test non-admin trying to get user favorites."""
        response = await authenticated_client.get(f"/api/v1/users/{test_user.id}/profile/favorites")
        assert response.status_code == 403


class TestUserDatabase:
    """Test user database operations."""

    async def test_create_user(
            self,
            db_session: AsyncSession,
            user_group: int
    ):
        """Test creating a user in the database."""
        user = User(
            email="db_test@example.com",
            hashed_password="hashed_password",
            is_active=True,
            group_id=user_group
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.id is not None
        assert user.email == "db_test@example.com"
        assert user.group_id == user_group

    async def test_user_relationships(
            self,
            test_user_with_profile: User
    ):
        """Test user model relationships."""
        assert test_user_with_profile.profile is not None
        assert test_user_with_profile.profile.first_name == "Test"
        assert test_user_with_profile.profile.last_name == "User"

    async def test_user_activation_token_relationship(
            self,
            inactive_user_with_token: User
    ):
        """Test user activation token relationship."""
        assert inactive_user_with_token.activation_token is not None
        assert inactive_user_with_token.activation_token.token is not None
        assert inactive_user_with_token.activation_token.user_id == inactive_user_with_token.id


class TestErrorHandling:
    """Test error handling scenarios."""

    async def test_profile_update_with_invalid_data(
            self,
            authenticated_client: AsyncClient
    ):
        """Test profile update with invalid data types."""
        invalid_data = {
            "first_name": 123,
            "last_name": [],
        }
        response = await authenticated_client.put("/api/v1/users/profile", json=invalid_data)
        assert response.status_code == 422

    async def test_activation_with_empty_token(
            self,
            async_client: AsyncClient
    ):
        """Test activation with empty token."""
        activation_data = {"token": ""}
        response = await async_client.post("/api/v1/users/activate", json=activation_data)
        assert response.status_code == 400

    async def test_role_change_with_invalid_role(
            self,
            admin_client: AsyncClient,
            test_user: User
    ):
        """Test role change with an invalid role."""
        role_data = {"new_role": "invalid_role"}
        response = await admin_client.post(f"/api/v1/users/{test_user.id}/change-role", json=role_data)
        assert response.status_code == 422
