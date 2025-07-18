import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from ..conftest import (
    create_unique_user,
    get_user_with_relationships
)
from users.models import User


@pytest.fixture
async def inactive_user(db_session: AsyncSession, user_group: int) -> User:
    """Create an inactive test user with unique email."""
    unique_email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(
        db_session,
        unique_email, "Testpassword_123",
        user_group,
        is_active=False
    )
    return await get_user_with_relationships(db_session, user.id)


@pytest.fixture
def invalid_login_data():
    """Invalid login data."""
    return {
        "email": "nonexistent@example.com",
        "password": "wrongpassword"
    }
