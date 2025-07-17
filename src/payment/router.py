import stripe
from fastapi import APIRouter, Depends, Query, HTTPException
from src.config.settings import settings
from src.payment.schemas import PaymentCreateSchema, PaymentSessionResponseSchema, PaymentResponseSchema
from src.payment.services import create_payment_session, get_user_payments

from src.config.database import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession

from src.payment.models import Payment
from src.users.dependencies import get_current_user
from src.users.models import User


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
        "amount": float(payment.amount),
        "created_at": payment.created_at
    }


@router.post("/", response_model=PaymentSessionResponseSchema)
async def create_payment(
    payload: PaymentCreateSchema,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    return await create_payment_session(payload, db, current_user)
