import uuid
import pytest
import time
import jwt
from datetime import datetime, timedelta
from decimal import Decimal
from httpx import AsyncClient
from sqlalchemy import insert, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.movies.models import Movie, FavoriteMoviesModel, PurchasedMovie, Certification
from src.orders.models import Order, OrderStatus, OrderItem
from src.payment.models import PaymentStatus, Payment
from src.tests.conftest import TestSessionLocal, create_unique_user, get_user_with_relationships
from src.users.models import User, UserProfile, UserGroupEnum, UserGroup
from src.users.utils.security import hash_password


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
    """Create a test user with sample purchased movies including full order flow."""
    user = test_user_with_profile

    # Create certification first
    cert = Certification(name="PG-13")
    db_session.add(cert)
    await db_session.commit()
    await db_session.refresh(cert)

    # Create movies
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
            certification_id=cert.id
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
            certification_id=cert.id
        )
    ]

    for movie in movies:
        db_session.add(movie)
    await db_session.commit()

    # Refresh movies to get their IDs
    for movie in movies:
        await db_session.refresh(movie)

    # Create orders and the complete purchase flow
    for i, movie in enumerate(movies):
        # 1. Create Order
        order = Order(
            user_id=user.id,
            total_amount=movie.price,
            status=OrderStatus.PAID,  # Use the enum value
            created_at=datetime.utcnow() - timedelta(days=5 - i)
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        # 2. Create OrderItem
        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(order_item)
        await db_session.commit()

        # 3. Create Payment
        payment = Payment(
            user_id=user.id,
            order_id=order.id,
            amount=movie.price,
            status=PaymentStatus.successful,  # Use the enum value
            created_at=datetime.utcnow() - timedelta(days=5 - i)
        )
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        # 4. Create PurchasedMovie
        purchase = PurchasedMovie(
            user_id=user.id,
            movie_id=movie.id,
            payment_id=payment.id,
            purchased_at=datetime.utcnow() - timedelta(days=5 - i)
        )
        db_session.add(purchase)

    await db_session.commit()

    # Store references for debugging
    user.test_movies = movies

    return user



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
