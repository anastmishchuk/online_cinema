import asyncio
from decimal import Decimal
import time
import jwt
import pytest
import uuid
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import StaticPool
from sqlalchemy import text, delete, insert
from datetime import datetime, timedelta
from unittest.mock import patch

from src.main import app
from src.config.database import get_async_db, Base
from src.config.settings import settings
from src.movies.models import PurchasedMovie, Movie, FavoriteMoviesModel
from src.users.models import User, UserGroup, UserProfile, UserGroupEnum
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


# Event loop configuration for pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures with proper cleanup
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


# HTTP Client fixtures
@pytest.fixture
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest.fixture(autouse=True)
async def cleanup_database(db_session: AsyncSession):
    """Automatically clean up database after each test."""
    yield
    try:
        await db_session.execute(delete(PurchasedMovie))
        await db_session.execute(delete(FavoriteMoviesModel))
        await db_session.execute(delete(Movie))
        await db_session.execute(delete(UserProfile))
        await db_session.execute(delete(User))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest.fixture(scope="session")
async def create_user_groups(setup_database):
    """Create all user groups once per session - depends on setup_database."""
    async with TestSessionLocal() as session:
        try:
            # Check if groups already exist
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
            raise


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


# Helper function to create unique users
async def create_unique_user(db_session: AsyncSession, email: str, password: str, group_id: int,
                             is_active: bool = True) -> User:
    """Create a unique user, handling duplicates."""
    # Clean up any existing user with this email first
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
    from sqlalchemy import select

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


# User fixtures with unique emails per test
@pytest.fixture
async def test_user(db_session: AsyncSession, user_group: int) -> User:
    """Create a test user with unique email."""
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Testpassword_123", user_group)
    # Load relationships to avoid greenlet issues
    return await get_user_with_relationships(db_session, user.id)


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


@pytest.fixture
async def test_admin(db_session: AsyncSession, admin_group: int) -> User:
    """Create a test admin user with unique email."""
    unique_email = f"admin_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Adminpassword_123", admin_group)
    return await get_user_with_relationships(db_session, user.id)


@pytest.fixture
async def test_moderator(db_session: AsyncSession, moderator_group: int) -> User:
    """Create a test moderator user with unique email."""
    unique_email = f"moderator_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Moderatorpassword_123", moderator_group)
    return await get_user_with_relationships(db_session, user.id)


@pytest.fixture
async def inactive_user(db_session: AsyncSession, user_group: int) -> User:
    """Create an inactive test user with unique email."""
    unique_email = f"inactive_{uuid.uuid4().hex[:8]}@example.com"
    user = await create_unique_user(db_session, unique_email, "Testpassword_123", user_group, is_active=False)
    return await get_user_with_relationships(db_session, user.id)


@pytest.fixture
async def authenticated_client(async_client: AsyncClient, test_user: User) -> AsyncClient:
    """Create an authenticated HTTP client."""
    # Generate JWT token for test user
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


# Authentication fixtures
@pytest.fixture
def valid_user_data():
    """Valid user registration data with unique email."""
    return {
        "email": f"newuser_{uuid.uuid4().hex[:8]}@example.com",
        "password": "Valid_password123",
        "confirm_password": "Valid_password123"
    }


@pytest.fixture
def invalid_user_data():
    """Invalid user registration data."""
    return {
        "email": "invalid-email",
        "password": "weak",
        "confirm_password": "different"
    }


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


# Token fixtures
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
        "exp": datetime.utcnow() - timedelta(minutes=1)  # Expired 1 minute ago
    }
    return jwt.encode(token_data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@pytest.fixture
def invalid_jwt_token() -> str:
    """Generate an invalid JWT token for testing."""
    return "invalid.jwt.token"


# Utility fixtures
@pytest.fixture
def mock_email_service(monkeypatch):
    """Mock email service for testing."""
    sent_emails = []

    def mock_send_email(to_email: str, subject: str, body: str):
        sent_emails.append({
            "to": to_email,
            "subject": subject,
            "body": body
        })

    return sent_emails


@pytest.fixture
def mock_stripe_service(monkeypatch):
    """Mock Stripe service for testing."""
    stripe_calls = []

    def mock_create_payment_intent(*args, **kwargs):
        stripe_calls.append(("create_payment_intent", args, kwargs))
        return {"id": "pi_test_123", "client_secret": "pi_test_123_secret"}

    def mock_create_customer(*args, **kwargs):
        stripe_calls.append(("create_customer", args, kwargs))
        return {"id": "cus_test_123"}

    return stripe_calls




@pytest.fixture
def sample_movie_data():
    """Sample movie data for testing."""
    return {
        "title": "Test Movie",
        "description": "A test movie description",
        "release_date": "2023-01-01",
        "duration": 120,
        "price": 9.99,
        "rating": 4.5
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "items": [
            {"movie_id": 1, "quantity": 1, "price": 9.99}
        ],
        "total_amount": 9.99,
        "payment_method": "card"
    }


# Performance testing fixtures
@pytest.fixture
async def performance_test_users(db_session: AsyncSession, user_group: int):
    """Create multiple users for performance testing with proper cleanup."""

    created_users = []

    async def _create_users(count: int = 100, prefix: str = None):
        nonlocal created_users
        if prefix is None:
            prefix = str(uuid.uuid4())[:8]

        await _cleanup_users_by_prefix(prefix)

        users = []
        for i in range(count):
            user = User(
                email=f"{prefix}_user{i}@example.com",
                hashed_password=hash_password("Testpassword_123"),
                is_active=True,
                group_id=user_group,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            users.append(user)

        db_session.add_all(users)
        await db_session.commit()
        created_users.extend(users)
        return users

    async def _cleanup_users_by_prefix(prefix):
        """Clean up users with specific prefix."""
        stmt = delete(User).where(User.email.like(f"{prefix}_user%@example.com"))
        await db_session.execute(stmt)
        await db_session.commit()

    yield _create_users

    # Cleanup after test
    if created_users:
        try:
            user_ids = [user.id for user in created_users if hasattr(user, 'id')]
            if user_ids:
                stmt = delete(User).where(User.id.in_(user_ids))
                await db_session.execute(stmt)
                await db_session.commit()
        except Exception:
            await db_session.rollback()


@pytest.fixture
async def inactive_user(db_session: AsyncSession, user_group: int):
    user = User(
        email="inactive@example.com",
        hashed_password=hash_password("Testpassword_123"),
        is_active=False,
        group_id=user_group
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def inactive_user_with_token(db_session: AsyncSession, user_group: int):
    from src.users.models import ActivationToken
    user = User(
        email="inactive_with_token@example.com",
        hashed_password=hash_password("Testpassword_123"),
        is_active=False,
        group_id=user_group
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await db_session.execute(
        delete(ActivationToken).where(ActivationToken.user_id == user.id)
    )
    await db_session.commit()

    expires_at = datetime.utcnow() + timedelta(hours=24)
    token = ActivationToken(
        token="test_activation_token",
        user_id=user.id,
        expires_at=expires_at
    )
    db_session.add(token)
    await db_session.commit()
    await db_session.refresh(token)

    user.activation_token = token
    return user


@pytest.fixture
async def admin_client_patched(async_client: AsyncClient, admin_user: User):
    # Mock authentication for admin user
    with patch("src.users.dependencies.get_current_user") as mock_get_user:
        mock_get_user.return_value = admin_user
        yield async_client


@pytest.fixture
async def admin_user(db_session: AsyncSession, admin_group: int):
    user = User(
        email="admin@example.com",
        hashed_password=hash_password("Testpassword_123"),
        is_active=True,
        group_id=admin_group
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_with_favorites(test_user_with_profile: User, db_session: AsyncSession) -> User:
    """Create a test user with favorite movies."""
    user = test_user_with_profile
    timestamp = int(time.time())
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    movies = [
        Movie(
            name=f"Action Hero Returns {timestamp}",  # Unique name
            year=2020,
            time=120,
            price=Decimal(9.99),
            description="Action movie from 2020",
            imdb=8.5,
            votes=1000,
            certification_id=1
        ),
        Movie(
            name=f"Space Warriors {timestamp}",  # Different name
            year=2020,  # Same year is OK
            time=110,
            price=Decimal(10.99),
            description="Another action movie from 2020",
            imdb=7.5,
            votes=800,
            certification_id=1
        ),
        Movie(
            name=f"Classic Drama {timestamp}",  # Different name
            year=2019,  # Different year
            time=100,
            price=Decimal(8.99),
            description="Drama from 2019",
            imdb=8.0,
            votes=1500,
            certification_id=1
        )
    ]

    for movie in movies:
        db_session.add(movie)
    await db_session.commit()

    for movie in movies:
        await db_session.refresh(movie)
        await db_session.execute(
            insert(FavoriteMoviesModel).values(
                user_id=user.id,
                movie_id=movie.id
            )
        )
    await db_session.commit()
    return user


@pytest.fixture
async def test_user_with_purchases(test_user_with_profile: User, db_session: AsyncSession):
    """Create a test user with sample purchased movies."""
    user = test_user_with_profile

    # Create sample movies for purchases
    movies = [
        Movie(
            name="Purchased Movie 1",
            year=2019,
            time=135,
            imdb=7.8,
            votes=12000,
            meta_score=78.0,
            gross=150000000.0,
            description="Drama movie for purchase testing",
            price=Decimal("14.99"),
            certification_id=1
        ),
        Movie(
            name="Purchased Movie 2",
            year=2022,
            time=105,
            imdb=7.2,
            votes=9000,
            meta_score=72.0,
            gross=80000000.0,
            description="Thriller movie for purchase testing",
            price=Decimal("11.99"),
            certification_id=1
        )
    ]

    for movie in movies:
        db_session.add(movie)
    await db_session.commit()

    for movie in movies:
        await db_session.refresh(movie)

    purchases = [
        PurchasedMovie(
            user_id=user.id,
            movie_id=movies[0].id,
            purchased_at=datetime.utcnow() - timedelta(days=5)
        ),
        PurchasedMovie(
            user_id=user.id,
            movie_id=movies[1].id,
            purchased_at=datetime.utcnow() - timedelta(days=2)
        )
    ]

    for purchase in purchases:
        db_session.add(purchase)
    await db_session.commit()

    user.test_movies = movies
    user.test_purchases = purchases

    return user



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
async def test_user_no_favorites(test_user_with_profile: User, db_session: AsyncSession) -> User:
    """Create a test user with no favorites."""
    user = test_user_with_profile
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_no_purchases(test_user_with_profile: User, db_session: AsyncSession) -> User:
    """Create a test user with no purchases."""
    user = test_user_with_profile
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user