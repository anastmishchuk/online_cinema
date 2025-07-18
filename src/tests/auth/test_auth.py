import secrets
from datetime import timedelta, datetime
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from users.models import User


class TestAuthentication:
    """Test authentication endpoints."""

    async def test_login_valid_credentials(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test login with valid credentials."""
        login_data = {
            "email": test_user.email,
            "password": "Testpassword_123"
        }
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_invalid_credentials(
            self,
            async_client: AsyncClient,
            invalid_login_data: dict
    ):
        """Test login with invalid credentials."""
        response = await async_client.post("/api/v1/auth/login", json=invalid_login_data)
        assert response.status_code == 401

    async def test_login_inactive_user(
            self,
            async_client: AsyncClient,
            inactive_user: User
    ):
        """Test login with inactive user."""
        login_data = {
            "email": inactive_user.email,
            "password": "Testpassword_123"
        }
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    async def test_login_missing_email(
            self,
            async_client: AsyncClient
    ):
        """Test login without email field."""
        login_data = {"password": "Testpassword_123"}
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422

    async def test_login_missing_password(
            self,
            async_client: AsyncClient
    ):
        """Test login without password field."""
        login_data = {"email": "test@example.com"}
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422

    async def test_login_empty_credentials(
            self,
            async_client: AsyncClient
    ):
        """Test login with empty credentials."""
        login_data = {"email": "", "password": ""}
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422

    async def test_login_nonexistent_user(
            self,
            async_client: AsyncClient
    ):
        """Test login with non-existent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "Testpassword_123"
        }
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401

    async def test_refresh_token_valid(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test refresh token with valid token."""
        login_data = {
            "email": test_user.email,
            "password": "Testpassword_123"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        tokens = login_response.json()

        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    async def test_refresh_token_invalid(
            self,
            async_client: AsyncClient
    ):
        """Test refresh token with invalid token."""
        refresh_data = {"refresh_token": "invalid_token"}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401

    async def test_refresh_token_expired(
            self,
            async_client: AsyncClient
    ):
        """Test refresh token with expired token."""
        with patch("users.auth.service.get_refresh_token") as mock_get_token:
            mock_token = AsyncMock()
            mock_token.is_expired.return_value = True
            mock_get_token.return_value = mock_token

            refresh_data = {"refresh_token": "expired_token"}
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            assert response.status_code == 401

    async def test_refresh_token_user_not_found(
            self,
            async_client: AsyncClient
    ):
        """Test refresh token when user no longer exists."""
        with patch("users.auth.service.get_refresh_token") as mock_get_token, \
                patch("users.auth.service.get_user_by_id") as mock_get_user, \
                patch("users.utils.security.decode_token") as mock_decode:
            mock_token = AsyncMock()
            mock_token.is_expired.return_value = False
            mock_get_token.return_value = mock_token
            mock_decode.return_value = {"sub": "999"}
            mock_get_user.return_value = None

            refresh_data = {"refresh_token": "valid_token"}
            response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
            assert response.status_code == 401

    async def test_refresh_token_missing_field(
            self,
            async_client: AsyncClient
    ):
        """Test refresh token without refresh_token field."""
        response = await async_client.post("/api/v1/auth/refresh", json={})
        assert response.status_code == 422

    async def test_logout_valid_token(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test logout with valid refresh token."""
        login_data = {
            "email": test_user.email,
            "password": "Testpassword_123"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        tokens = login_response.json()

        logout_data = {"refresh_token": tokens["refresh_token"]}
        response = await async_client.post("/api/v1/auth/logout", json=logout_data)
        assert response.status_code == 200
        assert response.json()["message"] == "Logged out successfully"

    async def test_logout_invalid_token(
            self,
            async_client: AsyncClient
    ):
        """Test logout with invalid refresh token."""
        logout_data = {"refresh_token": "invalid_token"}
        response = await async_client.post("/api/v1/auth/logout", json=logout_data)
        assert response.status_code == 404

    async def test_logout_missing_token(
            self,
            async_client: AsyncClient
    ):
        """Test logout without a refresh token."""
        response = await async_client.post("/api/v1/auth/logout", json={})
        assert response.status_code == 422

    async def test_logout_twice(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test logout twice with the same token."""
        login_data = {
            "email": test_user.email,
            "password": "Testpassword_123"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        tokens = login_response.json()

        logout_data = {"refresh_token": tokens["refresh_token"]}
        await async_client.post("/api/v1/auth/logout", json=logout_data)

        response = await async_client.post("/api/v1/auth/logout", json=logout_data)
        assert response.status_code == 404

    async def test_forgot_password_valid_email(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test forgot password with valid email."""
        with patch("users.service.send_password_reset_email") as mock_send:
            mock_send.return_value = AsyncMock()

            reset_data = {"email": test_user.email}
            response = await async_client.post("/api/v1/auth/password/forgot", json=reset_data)
            assert response.status_code == 200
            assert response.json()["message"] == "Password reset email sent"

    async def test_forgot_password_invalid_email(self, async_client: AsyncClient):
        """Test forgot password with non-existent email."""
        reset_data = {"email": "nonexistent@example.com"}
        response = await async_client.post("/api/v1/auth/password/forgot", json=reset_data)
        assert response.status_code == 404

    async def test_forgot_password_missing_email(self, async_client: AsyncClient):
        """Test forgot password without email."""
        response = await async_client.post("/api/v1/auth/password/forgot", json={})
        assert response.status_code == 422

    async def test_reset_password_valid_token(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test password reset with valid token."""
        with patch("users.auth.router.get_password_reset_token") as mock_get_token, \
                patch("users.auth.router.get_user_by_id") as mock_get_user, \
                patch("users.auth.router.update_user_password") as mock_update, \
                patch("users.auth.router.delete_password_reset_token") as mock_delete:
            token_value = secrets.token_urlsafe(32)

            mock_token = AsyncMock()
            mock_token.token = token_value
            mock_token.expires_at = datetime.utcnow() + timedelta(minutes=30)
            mock_token.user_id = test_user.id

            mock_get_token.return_value = mock_token
            mock_get_user.return_value = test_user
            mock_update.return_value = None
            mock_delete.return_value = None

            reset_data = {
                "token": token_value,
                "new_password": "NewPassword_123"
            }

            response = await async_client.post("/api/v1/auth/password/reset", json=reset_data)

            print(f"Response status code: {response.status_code}")
            print(f"Response JSON: {response.json()}")

            assert mock_get_token.called
            assert mock_get_user.called

            assert response.status_code == 200
            assert response.json()["message"] == "Password reset successfully"

    async def test_reset_password_invalid_token(self, async_client: AsyncClient):
        """Test password reset with invalid token."""
        reset_data = {
            "token": "invalid_token",
            "new_password": "NewPassword_123"
        }
        response = await async_client.post("/api/v1/auth/password/reset", json=reset_data)
        assert response.status_code == 400

    async def test_reset_password_expired_token(self, async_client: AsyncClient):
        """Test password reset with expired token."""
        with patch("users.auth.service.get_password_reset_token") as mock_get_token:
            mock_token = AsyncMock()
            mock_token.expires_at = datetime.utcnow() - timedelta(hours=1)
            mock_get_token.return_value = mock_token

            reset_data = {
                "token": "expired_token",
                "new_password": "NewPassword_123"
            }
            response = await async_client.post(
                "/api/v1/auth/password/reset",
                json=reset_data
            )
            assert response.status_code == 400

    async def test_reset_password_missing_fields(self, async_client: AsyncClient):
        """Test password reset with missing fields."""
        response = await async_client.post(
            "/api/v1/auth/password/reset",
            json={"new_password": "NewPassword_123"}
        )
        assert response.status_code == 422

        response = await async_client.post(
            "/api/v1/auth/password/reset",
            json={"token": "token"}
        )
        assert response.status_code == 422

    async def test_change_password_valid(
            self,
            async_client: AsyncClient,
            test_user: User,
            auth_headers: dict
    ):
        """Test password change with valid credentials."""
        change_data = {
            "old_password": "Testpassword_123",
            "new_password": "NewPassword_123"
        }
        response = await async_client.post(
            "/api/v1/auth/password/change",
            json=change_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Password changed successfully"

    async def test_change_password_wrong_old_password(
            self,
            async_client: AsyncClient,
            auth_headers: dict
    ):
        """Test password change with wrong old password."""
        change_data = {
            "old_password": "WrongPassword_123",
            "new_password": "NewPassword_123"
        }
        response = await async_client.post(
            "/api/v1/auth/password/change",
            json=change_data,
            headers=auth_headers
        )
        assert response.status_code == 400

    async def test_change_password_unauthorized(self, async_client: AsyncClient):
        """Test password change without authentication."""
        change_data = {
            "old_password": "Testpassword_123",
            "new_password": "NewPassword_123"
        }
        response = await async_client.post("/api/v1/auth/password/change", json=change_data)
        assert response.status_code == 401

    async def test_change_password_missing_fields(
            self,
            async_client: AsyncClient,
            auth_headers: dict
    ):
        """Test password change with missing fields."""
        response = await async_client.post(
            "/api/v1/auth/password/change",
            json={"new_password": "NewPassword_123"},
            headers=auth_headers
        )
        assert response.status_code == 422

        response = await async_client.post(
            "/api/v1/auth/password/change",
            json={"old_password": "Testpassword_123"},
            headers=auth_headers
        )
        assert response.status_code == 422

    async def test_sql_injection_attempt(self, async_client: AsyncClient):
        """Test SQL injection attempts in login."""
        malicious_data = {
            "email": "test@example.com'; DROP TABLE users; --",
            "password": "password"
        }
        response = await async_client.post("/api/v1/auth/login", json=malicious_data)
        assert response.status_code in [401, 422]

    async def test_very_long_input_fields(self, async_client: AsyncClient):
        """Test very long input fields."""
        long_string = "a" * 10000
        login_data = {
            "email": long_string,
            "password": long_string
        }
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code in [401, 422]

    async def test_token_reuse_after_logout(
            self,
            async_client: AsyncClient,
            test_user: User
    ):
        """Test that tokens can't be reused after logout."""
        login_data = {
            "email": test_user.email,
            "password": "Testpassword_123"
        }
        login_response = await async_client.post("/api/v1/auth/login", json=login_data)
        tokens = login_response.json()

        logout_data = {"refresh_token": tokens["refresh_token"]}
        await async_client.post("/api/v1/auth/logout", json=logout_data)

        refresh_data = {"refresh_token": tokens["refresh_token"]}
        response = await async_client.post("/api/v1/auth/refresh", json=refresh_data)
        assert response.status_code == 401

    async def test_malformed_json_requests(self, async_client: AsyncClient):
        """Test malformed JSON requests."""
        response = await async_client.post(
            "/api/v1/auth/login",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    async def test_content_type_validation(self, async_client: AsyncClient):
        """Test requests with the wrong content type."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data="email=test@example.com&password=password",
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422
