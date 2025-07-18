import uuid
import pytest
import time
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import insert, delete
from sqlalchemy.ext.asyncio import AsyncSession

from movies.models import (
    Movie,
    FavoriteMoviesModel,
    PurchasedMovie,
    Certification
)
from orders.models import (
    Order,
    OrderStatus,
    OrderItem
)
from payment.models import PaymentStatus, Payment
from users.models import User
from users.utils.security import hash_password


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
async def inactive_user(
        db_session: AsyncSession,
        user_group: int
):
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
async def inactive_user_with_token(
        db_session: AsyncSession,
        user_group: int
):
    from users.models import ActivationToken
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
async def test_user_with_favorites(
        test_user_with_profile: User,
        db_session: AsyncSession
) -> User:
    """Create a test user with favorite movies."""
    user = test_user_with_profile
    timestamp = int(time.time())
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    movies = [
        Movie(
            name=f"Action Hero Returns {timestamp}",
            year=2020,
            time=120,
            price=Decimal(9.99),
            description="Action movie from 2020",
            imdb=8.5,
            votes=1000,
            certification_id=1
        ),
        Movie(
            name=f"Space Warriors {timestamp}",
            year=2020,
            time=110,
            price=Decimal(10.99),
            description="Another action movie from 2020",
            imdb=7.5,
            votes=800,
            certification_id=1
        ),
        Movie(
            name=f"Classic Drama {timestamp}",
            year=2019,
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
async def test_user_with_purchases(
        test_user_with_profile: User,
        db_session: AsyncSession
):
    """Create a test user with sample purchased movies including full order flow."""
    user = test_user_with_profile

    cert = Certification(name="PG-13")
    db_session.add(cert)
    await db_session.commit()
    await db_session.refresh(cert)

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

    for movie in movies:
        await db_session.refresh(movie)

    for i, movie in enumerate(movies):
        order = Order(
            user_id=user.id,
            total_amount=movie.price,
            status=OrderStatus.PAID,
            created_at=datetime.utcnow() - timedelta(days=5 - i)
        )
        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(order_item)
        await db_session.commit()

        payment = Payment(
            user_id=user.id,
            order_id=order.id,
            amount=movie.price,
            status=PaymentStatus.successful,
            created_at=datetime.utcnow() - timedelta(days=5 - i)
        )
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        purchase = PurchasedMovie(
            user_id=user.id,
            movie_id=movie.id,
            payment_id=payment.id,
            purchased_at=datetime.utcnow() - timedelta(days=5 - i)
        )
        db_session.add(purchase)

    await db_session.commit()

    user.test_movies = movies

    return user


@pytest.fixture
async def test_user_no_favorites(
        test_user_with_profile: User,
        db_session: AsyncSession
) -> User:
    """Create a test user with no favorites."""
    user = test_user_with_profile
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def test_user_no_purchases(
        test_user_with_profile: User,
        db_session: AsyncSession
) -> User:
    """Create a test user with no purchases."""
    user = test_user_with_profile
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
