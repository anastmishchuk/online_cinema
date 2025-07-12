from decimal import Decimal
from typing import List

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.orders.models import Order, OrderItem, OrderStatus
from src.movies.models import Movie
from src.users.models import User
from src.users.utils.email import send_email
from src.cart.models import Cart, CartItem


async def create_order_from_cart(user: User, db: AsyncSession) -> Order:
    stmt = (
        select(CartItem.movie_id)
        .join(Cart, Cart.id == CartItem.cart_id)
        .where(Cart.user_id == user.id)
    )
    cart_ids = [row.movie_id for row in (await db.execute(stmt)).all()]

    if not cart_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your cart is empty."
        )

    available_movies_stmt = (
        select(Movie)
        .where(
            Movie.id.in_(cart_ids),
        )
    )
    available_movies = (await db.execute(available_movies_stmt)).scalars().all()

    if not available_movies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available movies in cart."
        )

    already_bought_stmt = (
        select(OrderItem.movie_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.user_id == user.id, Order.status == OrderStatus.PAID)
    )
    already_bought_ids = {row.movie_id for row in (await db.execute(already_bought_stmt)).all()}

    filtered_movies = [movie for movie in available_movies if movie.id not in already_bought_ids]
    if not filtered_movies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All movies are already purchased."
        )

    pending_stmt = (
        select(OrderItem.movie_id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.user_id == user.id, Order.status == OrderStatus.PENDING)
    )
    pending_movie_ids = {row.movie_id for row in (await db.execute(pending_stmt)).all()}

    final_movies = [m for m in filtered_movies if m.id not in pending_movie_ids]
    if not final_movies:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All movies are already pending in another order."
        )

    total_amount = sum(m.price for m in final_movies)

    order = Order(
        user_id=user.id,
        total_amount=Decimal(total_amount),
        status=OrderStatus.PENDING
    )
    db.add(order)
    await db.flush()

    for movie in final_movies:
        db.add(OrderItem(order_id=order.id, movie_id=movie.id, price_at_order=movie.price))

    cart_id_stmt = select(Cart.id).where(Cart.user_id == user.id)
    cart_id = (await db.execute(cart_id_stmt)).scalar_one_or_none()
    if cart_id:
        await db.execute(
            delete(CartItem).where(
                CartItem.cart_id == cart_id
            )
        )

    await db.commit()
    await db.refresh(order, attribute_names=["items"])

    return order


async def get_user_orders(user: User, db: AsyncSession) -> List[Order]:
    stmt = (
        select(Order)
        .where(Order.user_id == user.id)
        .order_by(Order.created_at.desc())
        .options(
            selectinload(Order.items).selectinload(OrderItem.movie)
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def mark_order_ready_for_payment(order: Order, db: AsyncSession) -> Order:
    order.is_confirmed = True
    await db.commit()
    await db.refresh(order)
    return order


async def send_payment_confirmation(to_email: str, order: Order):
    subject = f"Order #{order.id} payment confirmation"
    body = (
        f"Dear customer {order.user.profile.first_name},\n\n"
        f"Thank you for your payment. Your order #{order.id} has been successfully processed.\n"
        f"Order details:\n"
        f"- Total amount: ${order.total_amount}\n"
        f"- Status: {order.status.name}\n\n"
        f"Best regards,\n"
        f"{settings.PROJECT_NAME} Team"
    )
    await send_email(to_email, subject, body)


async def revalidate_order_total(order: Order, db: AsyncSession) -> dict:
    stmt = select(OrderItem).where(OrderItem.order_id == order.id)
    items = (await db.execute(stmt)).scalars().all()
    actual_total = sum(item.price_at_order for item in items)

    if order.total_amount != Decimal(actual_total):
        order.total_amount = Decimal(actual_total)
        await db.commit()
        await db.refresh(order)
        return {"changed": True, "new_total": Decimal(actual_total)}

    return {"changed": False}


async def process_order_payment(order: Order, user: User, db: AsyncSession) -> Order:
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not in pending status"
        )

    order.status = OrderStatus.PAID
    await db.commit()
    await db.refresh(order)

    await send_payment_confirmation(user.email, order)
    return order


async def get_order_by_id(order_id: int, user_id: int, db: AsyncSession) -> Order:
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.items))
    )
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise Exception(f"Order {order_id} not found or does not belong to the user")

    return order
