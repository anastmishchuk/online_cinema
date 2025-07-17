import stripe
from fastapi import APIRouter, Depends, HTTPException
from src.config.settings import settings
from src.payment.schemas import (
    PaymentCreateSchema,
    PaymentSessionResponseSchema,
    PaymentResponseSchema
)
from src.payment.service import create_payment_session, get_user_payments

from src.config.database import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment.models import Payment
from src.users.dependencies import get_current_user
from src.users.models import User
from src.orders.models import Order, OrderStatus
from src.orders.service import process_order_payment


stripe.api_key = settings.STRIPE_SECRET_KEY

router = APIRouter()


@router.get("/history", response_model=list[PaymentResponseSchema])
async def get_payment_history(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    payments = await get_user_payments(current_user.id, db)
    return payments


@router.get("/{payment_id}/status")
async def get_payment_status(
    payment_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    payment = await db.get(Payment, payment_id)

    if not payment or payment.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "payment_id": payment.id,
        "order_id": payment.order_id,
        "status": payment.status.value,
        "amount": payment.amount,
        "created_at": payment.created_at
    }


@router.get("/{payment_id}/status/success")
async def payment_success(
        payment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user)
):
    """Handle successful payment redirect from Stripe"""
    try:
        payment = await db.get(Payment, payment_id)
        if not payment or payment.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Payment not found")

        payment.status = "successful"

        order = await db.get(Order, payment.order_id)
        if order:
            await process_order_payment(order, current_user, db)

        await db.commit()

        return {
            "message": "Payment successful",
            "payment_id": payment.id,
            "redirect_url":
                f"{settings.BASE_URL}/{settings.PAYMENTS_ROUTE_PREFIX}/{payment.id}/status"
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing payment: {str(e)}")


@router.get("/{payment_id}/status/cancel")
async def payment_cancel(
        payment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user)
):
    """Handle cancelled payment redirect from Stripe"""
    try:
        payment = await db.get(Payment, payment_id)
        if not payment or payment.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Payment not found")

        payment.status = "canceled"

        order = await db.get(Order, payment.order_id)
        if order:
            order.status = OrderStatus.CANCELED

        await db.commit()

        return {
            "message": "Payment cancelled",
            "payment_id": payment.id
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error cancelling payment: {str(e)}")


@router.post("/", response_model=PaymentSessionResponseSchema)
async def create_payment(
    payload: PaymentCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    payment_session = await create_payment_session(payload, db, current_user)

    return payment_session
