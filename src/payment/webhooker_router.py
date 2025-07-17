import stripe
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import get_async_db
from src.config.settings import settings
from src.payment.services import handle_successful_checkout


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(
            payload=payload, sig_header=sig_header, secret=endpoint_secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        try:
            await handle_successful_checkout(session, db)
            logger.info(
                f"Processed successful checkout for user {session['metadata']['user_id']} "
                f"with order {session['metadata']['order_id']}")
        except Exception as e:
            logger.error(f"Failed to handle successful checkout: {e}")
            raise HTTPException(status_code=500, detail=f"Error processing payment: {str(e)}")

    elif event["type"] == "payment_intent.failed":
        payment_intent = event["data"]["object"]
        logger.error(
        f"Payment failed for user {payment_intent['metadata']['user_id']} "
        f"with order {payment_intent['metadata']['order_id']}")

    elif event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        logger.info(
            f"Payment succeeded for user {payment_intent['metadata']['user_id']} "
            f"with order {payment_intent['metadata']['order_id']}")

    else:
        logger.info(f"Unhandled Stripe event type: {event['type']}")

    return {"status": "success"}

