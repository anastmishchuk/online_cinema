import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from cart.models import CartItem, Cart
from users.models import User


@pytest.fixture
async def cart_with_items(
        db_session: AsyncSession,
        sample_user: User,
        sample_movies: dict
):
    """Create a cart with some items for testing"""
    cart = Cart(user_id=sample_user.id)
    db_session.add(cart)
    await db_session.commit()

    cart_item = CartItem(cart_id=cart.id, movie_id=sample_movies["movies"][0].id)
    db_session.add(cart_item)
    await db_session.commit()

    return {
        "cart": cart,
        "items": [cart_item]
    }
