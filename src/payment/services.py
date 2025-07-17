import stripe
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.config.settings import settings
from src.orders.models import OrderStatus
from src.orders.service import get_order_by_id
from src.payment.models import Payment, PaymentStatus, PaymentItem
from src.payment.schemas import PaymentCreateSchema, PaymentSessionResponseSchema
from src.users.models import User


async def handle_successful_checkout(session: dict, db: AsyncSession):
    metadata = session.get("metadata", {})
    if not metadata:
        raise ValueError("Missing metadata in Stripe session.")

    order_id = int(metadata.get("order_id"))
    user_id = int(metadata.get("user_id"))

    amount_total = session.get("amount_total")
    if amount_total is None:
        raise ValueError("Stripe session missing amount_total")

    order = await get_order_by_id(order_id, db)

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
    payment = Payment(
        user_id=current_user.id,
        order_id=payload.order_id,
        amount=payload.amount,
        status="pending",
    )
    db.add(payment)
    await db.flush()

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

    return PaymentSessionResponseSchema(
        checkout_url=checkout_session.url,
        payment_id=payment.id
    )


async def get_user_payments(user_id: int, db: AsyncSession) -> list[Payment]:
    stmt = (
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .options(selectinload(Payment.items))
    )
    result = await db.execute(stmt)
    return result.scalars().all()
