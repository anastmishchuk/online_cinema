import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from sqlalchemy.orm import selectinload

from config.database import get_async_db
from payment.schemas import PaymentCreateSchema
from payment.service import create_payment_session
from users.models import User
from users.dependencies import get_current_user
from .models import Order, OrderStatus, RefundRequest
from .schemas import OrderRead, RefundRequestCreate
from .service import (
    create_order_from_cart,
    get_user_orders,
    revalidate_order_total
)


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    order = await create_order_from_cart(user, db)
    return order


@router.get("/", response_model=List[OrderRead])
async def list_user_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await get_user_orders(user, db)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == user.id)
        .options(selectinload(Order.items))
    )
    order = (await db.execute(stmt)).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    return order


@router.post("/{order_id}/confirm", status_code=status.HTTP_303_SEE_OTHER, response_model=None)
async def confirm_order_and_redirect_to_payment(
        order_id: int,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
):
    """
    Confirm an order and redirect to payment.
    Returns a warning if order total has changed, otherwise redirects to payment.
    """
    stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()
    if not order or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=400, detail="Order cannot be confirmed")

    reval = await revalidate_order_total(order, db)
    if reval["changed"]:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "warning": (
                    f"Order total has changed to {reval['new_total']:.2f}. "
                    "Do you want to proceed?"
                ),
                "order": OrderRead.model_validate(order).model_dump(mode="json")
            }
        )

    payment_create_payload = PaymentCreateSchema(
        order_id=order.id,
        amount=order.total_amount
    )
    payment_session = await create_payment_session(payment_create_payload, db, user)

    return RedirectResponse(
        url=payment_session.checkout_url,
        status_code=status.HTTP_303_SEE_OTHER
    )


@router.post("/{order_id}/cancel/", status_code=status.HTTP_200_OK)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Order).where(
        Order.id == order_id, Order.user_id == current_user.id
    )
    order = (await db.execute(stmt)).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    if order.status == OrderStatus.CANCELED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already canceled."
        )

    if order.status == OrderStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Paid orders cannot be canceled directly. Please request a refund."
        )

    if order.status == OrderStatus.PENDING:
        order.status = OrderStatus.CANCELED
        await db.commit()
        return {"detail": "Order has been canceled."}

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="This order cannot be canceled."
    )


@router.post("/{order_id}/refund", status_code=status.HTTP_201_CREATED)
async def request_refund(
    order_id: int,
    payload: RefundRequestCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    order = (await db.execute(stmt)).scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found."
        )

    if order.status != OrderStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paid orders can be refunded."
        )

    refund_stmt = select(RefundRequest).where(RefundRequest.order_id == order.id)
    existing_refund = (await db.execute(refund_stmt)).scalar_one_or_none()

    if existing_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund request already submitted."
        )

    refund = RefundRequest(
        user_id=current_user.id,
        order_id=order.id,
        reason=payload.reason
    )
    db.add(refund)
    await db.commit()

    return {"detail": "Refund request submitted successfully."}
