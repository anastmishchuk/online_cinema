from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from src.users.models import User, UserGroupEnum


class TestDatabaseOperations:
    """Test database operations."""

    async def test_database_connection(self, db_session: AsyncSession):
        """Test database connection works."""
        result = await db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1

    async def test_user_group_relationship(self, test_user: User, user_group: int):
        """Test user-group relationship."""
        assert test_user.group_id == user_group
        assert test_user.group.name == UserGroupEnum.USER
