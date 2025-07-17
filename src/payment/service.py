import stripe
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config.settings import settings
from ..movies.crud.movies import purchase_movie
from ..orders.models import OrderStatus, Order
from ..orders.service import get_order_by_id
from ..users.models import User

from .models import Payment, PaymentStatus, PaymentItem
from .schemas import PaymentCreateSchema, PaymentSessionResponseSchema


async def handle_successful_checkout(session: dict, db: AsyncSession):
    metadata = session.get("metadata", {})
    if not metadata:
        raise ValueError("Missing metadata in Stripe session.")

    order_id = int(metadata.get("order_id"))
    user_id = int(metadata.get("user_id"))

    amount_total = session.get("amount_total")
    if amount_total is None:
        raise ValueError("Stripe session missing amount_total")

    order = await get_order_by_id(order_id, db=db, user_id=user_id)

    if order.status != OrderStatus.PAID:
        payment = Payment(
            user_id=user_id,
            order_id=order_id,
            amount=Decimal(session["amount_total"]) / 100,
            status=PaymentStatus.successful,
            external_payment_id=session["id"],
        )
        db.add(payment)
        await db.flush()

        for item in order.items:
            payment_item = PaymentItem(
                payment_id=payment.id,
                order_item_id=item.id,
                price_at_payment=item.price_at_order
            )
            db.add(payment_item)

        order.status = OrderStatus.PAID
        await db.commit()



async def create_payment_session(
    payload: PaymentCreateSchema,
    db: AsyncSession,
    current_user: User
) -> PaymentSessionResponseSchema:

    existing_payment_result = await db.execute(
        select(Payment).filter(Payment.external_payment_id == payload.external_payment_id)
    )
    existing_payment = existing_payment_result.scalars().first()

    if existing_payment:
        payment = existing_payment
        payment.status = PaymentStatus.successful
        payment.created_at = datetime.utcnow()
    else:
        payment = Payment(
            user_id=current_user.id,
            order_id=payload.order_id,
            amount=payload.amount,
            status=PaymentStatus.successful,
            created_at=datetime.utcnow()
        )
        db.add(payment)

    await db.commit()
    await db.refresh(payment)

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": f"Order #{payload.order_id}",
                    },
                    "unit_amount": int(payload.amount * Decimal("100")),
                },
                "quantity": 1,
            }
        ],
        metadata={
            "order_id": str(payload.order_id),
            "user_id": str(current_user.id),
        },
        success_url=f"{settings.BASE_URL}{settings.API_VERSION_PREFIX}/payment/{payment.id}/status/success",
        cancel_url=f"{settings.BASE_URL}{settings.API_VERSION_PREFIX}/payment/{payment.id}/status/cancel"
    )

    payment.external_payment_id = checkout_session.id
    await db.commit()
    await db.refresh(payment)

    order_stmt = select(Order).options(
        selectinload(Order.items)
    ).where(Order.id == payload.order_id)

    order_result = await db.execute(order_stmt)
    order = order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    for order_item in order.items:
        movie_id = order_item.movie_id
        await purchase_movie(db, current_user.id, movie_id, payment.id)

    return PaymentSessionResponseSchema(
        checkout_url=checkout_session.url,
        payment_id=payment.id
    )


async def get_user_payments(user_id: int, db: AsyncSession) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .options(
            selectinload(Payment.items),
            selectinload(Payment.order),
            selectinload(Payment.user)
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()
