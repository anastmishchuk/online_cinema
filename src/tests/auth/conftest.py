import uuid
from datetime import datetime, timedelta

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.tests.conftest import create_unique_user, get_user_with_relationships
from src.users.models import User


@pytest.fixture
async def inactive_user(db_session: AsyncSession, user_group: int) -> User:
    """Create an inactive test user with unique email."""
    unique_email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Testpassword_123", user_group, is_active=False)
    return await get_user_with_relationships(db_session, user.id)



@pytest.fixture
def valid_login_data(test_user: User):
    """Valid login data using the test user's email."""
    return {
        "email": test_user.email,
        "password": "Testpassword_123"
    }


@pytest.fixture
def invalid_login_data():
    """Invalid login data."""
    return {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }


@pytest.fixture
def valid_jwt_token(test_user: User) -> str:
    """Generate a valid JWT token for testing."""
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "group": test_user.group.name.value,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    return jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def expired_jwt_token(test_user: User) -> str:
    """Generate an expired JWT token for testing."""
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "group": test_user.group.name.value,
        "exp": datetime.utcnow() - timedelta(minutes=1)
    }
    return jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def invalid_jwt_token() -> str:
    """Generate an invalid JWT token for testing."""
    return "invalid.jwt.token"

