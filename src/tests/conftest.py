import asyncio

import jwt
import pytest
import uuid
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool
from sqlalchemy import delete, text, select
from datetime import datetime, timedelta

from src.cart.models import Cart, CartItem
from src.config.settings import settings
from src.main import app
from src.config.database import get_async_db, Base
from src.movies.models import (
    PurchasedMovie,
    Movie,
    FavoriteMoviesModel,
    Director,
    Star,
    Genre,
    Certification,
    MoviesDirectorsModel,
    MoviesStarsModel,
    MoviesGenresModel,
    MovieRating,
    Comment,
    Like
)
from src.orders.models import Order, OrderItem, RefundRequest
from src.payment.models import PaymentItem, Payment
from src.users.models import User, UserProfile, UserGroupEnum, UserGroup
from src.users.utils.security import hash_password


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
    echo=False
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a database session for testing with proper cleanup."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest.fixture
async def override_get_db(db_session: AsyncSession):
    """Override the get_async_db dependency."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db] = _override_get_db
    yield
    app.dependency_overrides = {}


@pytest.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest.fixture(autouse=True)
async def cleanup_database(db_session: AsyncSession):
    """Automatically clean up database before andafter each test."""
    try:
        await db_session.execute(delete(MoviesDirectorsModel))
        await db_session.execute(delete(MoviesStarsModel))
        await db_session.execute(delete(MoviesGenresModel))
        await db_session.execute(delete(FavoriteMoviesModel))
        await db_session.execute(delete(PurchasedMovie))
        await db_session.execute(delete(Like))
        await db_session.execute(delete(Comment))
        await db_session.execute(delete(MovieRating))
        await db_session.execute(delete(Movie))
        await db_session.execute(delete(Star))
        await db_session.execute(delete(Director))
        await db_session.execute(delete(Genre))
        await db_session.execute(delete(Certification))
        await db_session.execute(delete(UserProfile))
        await db_session.execute(delete(User))
        await db_session.execute(delete(Cart))
        await db_session.execute(delete(CartItem))
        await db_session.execute(delete(Order))
        await db_session.execute(delete(OrderItem))
        await db_session.execute(delete(RefundRequest))
        await db_session.execute(delete(Payment))
        await db_session.execute(delete(PaymentItem))
        await db_session.commit()
    except Exception:
        await db_session.rollback()

    yield

    try:
        await db_session.execute(delete(MoviesDirectorsModel))
        await db_session.execute(delete(MoviesStarsModel))
        await db_session.execute(delete(MoviesGenresModel))
        await db_session.execute(delete(FavoriteMoviesModel))
        await db_session.execute(delete(PurchasedMovie))
        await db_session.execute(delete(Like))
        await db_session.execute(delete(Comment))
        await db_session.execute(delete(MovieRating))
        await db_session.execute(delete(Movie))
        await db_session.execute(delete(Star))
        await db_session.execute(delete(Director))
        await db_session.execute(delete(Genre))
        await db_session.execute(delete(Certification))
        await db_session.execute(delete(UserProfile))
        await db_session.execute(delete(User))
        await db_session.execute(delete(Cart))
        await db_session.execute(delete(CartItem))
        await db_session.execute(delete(Order))
        await db_session.execute(delete(OrderItem))
        await db_session.execute(delete(RefundRequest))
        await db_session.execute(delete(Payment))
        await db_session.execute(delete(PaymentItem))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest.fixture(scope="session")
async def create_user_groups(setup_database):
    """Create all user groups once per session - depends on setup_database."""
    async with TestSessionLocal() as session:
        try:
            existing_groups = await session.execute(text("SELECT name FROM user_groups"))
            existing_names = {row[0] for row in existing_groups.fetchall()}

            groups_to_create = []
            for group_enum in UserGroupEnum:
                if group_enum.value not in existing_names:
                    groups_to_create.append(UserGroup(name=group_enum))

            if groups_to_create:
                session.add_all(groups_to_create)
                await session.commit()

            result = await session.execute(text("SELECT id, name FROM user_groups"))
            groups = {row[1]: row[0] for row in result.fetchall()}
            return groups
        except Exception as e:
            await session.rollback()
            raise e


@pytest.fixture
async def user_group(create_user_groups) -> int:
    """Get USER group ID."""
    return create_user_groups[UserGroupEnum.USER.value]


@pytest.fixture
async def moderator_group(create_user_groups) -> int:
    """Get MODERATOR group ID."""
    return create_user_groups[UserGroupEnum.MODERATOR.value]


@pytest.fixture
async def admin_group(create_user_groups) -> int:
    """Get ADMIN group ID."""
    return create_user_groups[UserGroupEnum.ADMIN.value]


async def create_unique_user(db_session: AsyncSession, email: str, password: str, group_id: int,
                             is_active: bool = True) -> User:
    """Create a unique user, handling duplicates."""
    await db_session.execute(delete(User).where(User.email == email))
    await db_session.commit()

    user = User(
        email=email,
        hashed_password=hash_password(password),
        is_active=is_active,
        group_id=group_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def get_user_with_relationships(db_session: AsyncSession, user_id: int) -> User:
    """Get user with all relationships properly loaded."""

    stmt = select(User).options(
        selectinload(User.profile),
        selectinload(User.group),
        selectinload(User.favorite_movies),
        selectinload(User.likes),
        selectinload(User.movie_ratings),
        selectinload(User.purchased_movies),
        selectinload(User.cart),
        selectinload(User.orders),
        selectinload(User.payments),
        selectinload(User.refund_requests),
    ).where(User.id == user_id)

    result = await db_session.execute(stmt)
    return result.scalar_one()


@pytest.fixture
async def test_user(db_session: AsyncSession, user_group: int) -> User:
    """Create a test user with unique email."""
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Testpassword_123", user_group)
    return await get_user_with_relationships(db_session, user.id)


@pytest.fixture
async def test_moderator(db_session: AsyncSession, moderator_group: int) -> User:
    """Create a test moderator user with unique email."""
    unique_email = f"moderator_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Moderatorpassword_123", moderator_group)
    return await get_user_with_relationships(db_session, user.id)


@pytest.fixture
async def test_admin(db_session: AsyncSession, admin_group: int) -> User:
    """Create a test admin user with unique email."""
    unique_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Adminpassword_123", admin_group)
    return await get_user_with_relationships(db_session, user.id)


@pytest.fixture
async def auth_headers(async_client: AsyncClient, test_user: User):
    """Get authentication headers for a test user."""
    login_data = {
        "email": test_user.email,
        "password": "Testpassword_123"
    }
    response = await async_client.post("/api/v1/auth/login", json=login_data)
    tokens = response.json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.fixture
async def authenticated_client(async_client: AsyncClient, test_user: User) -> AsyncClient:
    """Create an authenticated HTTP client."""
    token_data = {
        "sub": str(test_user.id),
        "email": test_user.email,
        "group": test_user.group.name.value,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    token = jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async_client.headers.update({"Authorization": f"Bearer {token}"})
    return async_client


@pytest.fixture
async def admin_client(async_client: AsyncClient, test_admin: User) -> AsyncClient:
    """Create an authenticated HTTP client for admin user."""
    token_data = {
        "sub": str(test_admin.id),
        "email": test_admin.email,
        "group": test_admin.group.name.value,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    token = jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async_client.headers.update({"Authorization": f"Bearer {token}"})
    return async_client


@pytest.fixture
async def moderator_client(async_client: AsyncClient, test_moderator: User) -> AsyncClient:
    """Create an authenticated HTTP client for moderator user."""
    token_data = {
        "sub": str(test_moderator.id),
        "email": test_moderator.email,
        "group": test_moderator.group.name.value,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    }
    token = jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    async_client.headers.update({"Authorization": f"Bearer {token}"})
    return async_client


@pytest.fixture
async def test_user_with_profile(db_session: AsyncSession, test_user: User) -> User:
    """Create a test user with profile and all relationships loaded."""
    user = await create_unique_user(
        db_session=db_session,
        email=test_user.email,
        password=test_user.hashed_password,
        is_active=test_user.is_active,
        group_id=test_user.group_id,
    )

    profile = UserProfile(
        user_id=test_user.id,
        first_name="Test",
        last_name="User",
        date_of_birth=datetime(1990, 1, 1),
        info="Test user profile"
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    user_with_relationships = await get_user_with_relationships(db_session, user.id)

    if user_with_relationships.profile is None:
        raise Exception(f"Profile not loaded for user {user.id}")

    return user_with_relationships
