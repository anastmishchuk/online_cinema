import pytest
import stripe
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.payment.models import PaymentItem
from src.payment.schemas import (
    PaymentCreateSchema,
    PaymentSessionResponseSchema
)
from src.payment.services import (
    create_payment_session,
    get_user_payments,
    handle_successful_checkout
)
from src.orders.models import Order, OrderStatus, OrderItem
from src.payment.models import Payment, PaymentStatus
from src.users.models import User
from src.users.utils.security import hash_password


class TestPaymentServices:
    """Test payment service functions"""

    @patch("stripe.checkout.Session.create")
    @patch("src.movies.crud.movies.purchase_movie")
    async def test_create_payment_session_success(
            self,
            mock_purchase_movie: AsyncMock,
            mock_stripe_session: MagicMock,
            db_session: AsyncSession,
            test_user: User,
            sample_order: Order
    ):
        """Test successful payment session creation"""
        mock_stripe_session.return_value = MagicMock(
            id="cs_test_123456",
            url="https://checkout.stripe.com/test"
        )
        mock_purchase_movie.return_value = None

        order_id = sample_order.id

        payload = PaymentCreateSchema(
            order_id=order_id,
            amount=Decimal("9.99"),
            external_payment_id="cs_test_123456"
        )

        result = await create_payment_session(payload, db_session, test_user)

        assert isinstance(result, PaymentSessionResponseSchema)
        assert result.checkout_url == "https://checkout.stripe.com/test"
        assert result.payment_id is not None

        payment = await db_session.get(Payment, result.payment_id)
        assert payment is not None
        assert payment.user_id == test_user.id
        assert payment.order_id == order_id
        assert payment.amount == Decimal("9.99")
        assert payment.status == PaymentStatus.successful
        assert payment.external_payment_id == "cs_test_123456"

    @patch("stripe.checkout.Session.create")
    async def test_create_payment_session_existing_payment(
            self,
            mock_stripe_session: MagicMock,
            db_session: AsyncSession,
            test_user: User,
            sample_order: Order,
            sample_payment: Payment
    ):
        """Test payment session creation with existing payment"""
        mock_stripe_session.return_value = MagicMock(
            id="cs_test_123456",
            url="https://checkout.stripe.com/test"
        )

        payload = PaymentCreateSchema(
            order_id=sample_order.id,
            amount=Decimal("9.99"),
            external_payment_id="cs_test_123456"
        )

        result = await create_payment_session(payload, db_session, test_user)

        assert isinstance(result, PaymentSessionResponseSchema)
        assert result.payment_id == sample_payment.id

        updated_payment = await db_session.get(Payment, sample_payment.id)
        assert updated_payment.status == PaymentStatus.successful

    @patch("stripe.checkout.Session.create")
    async def test_create_payment_session_order_not_found(
            self,
            mock_stripe_session: MagicMock,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test payment session creation with non-existent order"""
        mock_stripe_session.return_value = MagicMock(
            id="cs_test_123456",
            url="https://checkout.stripe.com/test"
        )

        payload = PaymentCreateSchema(
            order_id=99999,
            amount=Decimal("9.99"),
            external_payment_id="cs_test_123456"
        )

        with pytest.raises(HTTPException) as exc_info:
            await create_payment_session(payload, db_session, test_user)

        assert exc_info.value.status_code == 404
        assert "Order not found" in str(exc_info.value.detail)

    async def test_get_user_payments(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_payment: Payment
    ):
        """Test retrieving user payments"""
        payments = await get_user_payments(test_user.id, db_session)

        assert len(payments) == 1
        assert payments[0].id == sample_payment.id
        assert payments[0].user_id == test_user.id
        assert payments[0].amount == Decimal("9.99")

    async def test_get_user_payments_empty(
            self,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test retrieving payments for user with no payments"""
        payments = await get_user_payments(test_user.id, db_session)
        assert len(payments) == 0

    async def test_handle_successful_checkout(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_order: Order
    ):
        """Test successful checkout handling"""
        stripe_session = {
            "id": "cs_test_123456",
            "amount_total": 999,
            "metadata": {
                "order_id": str(sample_order.id),
                "user_id": str(test_user.id)
            }
        }

        await handle_successful_checkout(stripe_session, db_session)

        payment_result = await db_session.execute(
            select(Payment).where(Payment.external_payment_id == "cs_test_123456")
        )
        payment = payment_result.scalar_one()

        assert payment.user_id == test_user.id
        assert payment.order_id == sample_order.id
        assert payment.amount == Decimal("9.99")
        assert payment.status == PaymentStatus.successful

        await db_session.refresh(sample_order)
        assert sample_order.status == OrderStatus.PAID

    async def test_handle_successful_checkout_missing_metadata(
            self,
            db_session: AsyncSession
    ):
        """Test checkout handling with missing metadata"""
        stripe_session = {
            "id": "cs_test_123456",
            "amount_total": 1999,
            "metadata": {}
        }

        with pytest.raises(ValueError) as exc_info:
            await handle_successful_checkout(stripe_session, db_session)

        assert "Missing metadata in Stripe session" in str(exc_info.value)

    async def test_handle_successful_checkout_missing_amount(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_order: Order
    ):
        """Test checkout handling with missing amount"""
        stripe_session = {
            "id": "cs_test_123456",
            "metadata": {
                "order_id": str(sample_order.id),
                "user_id": str(test_user.id)
            }
        }

        with pytest.raises(ValueError) as exc_info:
            await handle_successful_checkout(stripe_session, db_session)

        assert "Stripe session missing amount_total" in str(exc_info.value)


class TestPaymentAPI:
    """Test payment API endpoints"""

    async def test_get_payment_history(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_payment: Payment,
            sample_order: Order
    ):
        """Test getting payment history"""
        response = await authenticated_client.get("/api/v1/payment/history")

        assert response.status_code == 200
        payments = response.json()
        assert len(payments) == 1

        payment_data = payments[0]
        assert payment_data["id"] == sample_payment.id
        assert payment_data["amount"] == str(sample_payment.amount)
        assert payment_data["status"] == sample_payment.status.value
        assert payment_data["external_payment_id"] == sample_payment.external_payment_id
        assert payment_data["order_id"] == sample_order.id

    async def test_get_payment_history_empty(
            self,
            authenticated_client: AsyncClient
    ):
        """Test getting empty payment history"""
        response = await authenticated_client.get("/api/v1/payment/history")

        assert response.status_code == 200
        payments = response.json()
        assert len(payments) == 0

    async def test_get_payment_status(
            self,
            authenticated_client: AsyncClient,
            sample_payment: Payment
    ):
        """Test getting payment status"""
        response = await authenticated_client.get(f"/api/v1/payment/{sample_payment.id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["payment_id"] == sample_payment.id
        assert data["status"] == PaymentStatus.successful.value
        assert data["amount"] == float(sample_payment.amount)

    async def test_get_payment_status_not_found(
            self,
            authenticated_client: AsyncClient
    ):
        """Test getting status for non-existent payment"""
        response = await authenticated_client.get("/api/v1/payment/99999/status")

        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

    async def test_get_payment_status_unauthorized(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            user_group: int
    ):
        """Test getting payment status for another user's payment"""
        other_user = User(
            email="other@example.com",
            hashed_password=hash_password("password"),
            group_id=user_group
        )
        db_session.add(other_user)
        await db_session.flush()

        payment = Payment(
            user_id=other_user.id,
            order_id=1,
            amount=Decimal("9.99"),
            status=PaymentStatus.successful
        )
        db_session.add(payment)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/v1/payment/{payment.id}/status")

        assert response.status_code == 404
        assert "Payment not found" in response.json()["detail"]

    @patch("src.payment.router.process_order_payment")
    async def test_payment_success(
            self,
            mock_process_order: AsyncMock,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            sample_payment: Payment,
            sample_order: Order
    ):
        """Test successful payment callback"""
        mock_process_order.return_value = None

        response = await authenticated_client.get(
            f"/api/v1/payment/{sample_payment.id}/status/success"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Payment successful"
        assert data["payment_id"] == sample_payment.id
        assert "redirect_url" in data

        await db_session.refresh(sample_payment)
        assert sample_payment.status == PaymentStatus.successful

    async def test_payment_cancel(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            sample_payment: Payment,
            sample_order: Order
    ):
        """Test payment cancellation callback"""
        response = await authenticated_client.get(
            f"/api/v1/payment/{sample_payment.id}/status/cancel"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Payment cancelled"
        assert data["payment_id"] == sample_payment.id

        await db_session.refresh(sample_payment)
        assert sample_payment.status == PaymentStatus.canceled

        await db_session.refresh(sample_order)
        assert sample_order.status == OrderStatus.CANCELED

    @patch("src.payment.router.create_payment_session")
    async def test_create_payment_endpoint(
            self,
            mock_create_payment: AsyncMock,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            sample_order: Order
    ):
        """Test payment creation endpoint"""
        mock_create_payment.return_value = PaymentSessionResponseSchema(
            checkout_url="https://checkout.stripe.com/test",
            payment_id=1
        )

        payload = {
            "order_id": sample_order.id,
            "amount": 9.99,
            "external_payment_id": "cs_test_123456"
        }

        response = await authenticated_client.post("/api/v1/payment/", json=payload)

        assert response.status_code == 200
        data = response.json()
        mock_create_payment.assert_called_once()

        assert "checkout_url" in data
        assert data["checkout_url"].startswith("https://checkout.stripe.com/")
        assert "payment_id" in data
        assert isinstance(data["payment_id"], int)

    async def test_create_payment_invalid_data(
            self,
            authenticated_client: AsyncClient
    ):
        """Test payment creation with invalid data"""
        payload = {
            "order_id": "invalid",
            "amount": "invalid",
        }

        response = await authenticated_client.post("/api/v1/payment/", json=payload)

        assert response.status_code == 422


class TestStripeWebhook:
    """Test Stripe webhook handling"""

    @patch("stripe.Webhook.construct_event")
    @patch("src.payment.webhooker_router.handle_successful_checkout")
    async def test_stripe_webhook_checkout_completed(
            self,
            mock_handle_checkout: AsyncMock,
            mock_construct_event: MagicMock,
            async_client: AsyncClient,
            db_session: AsyncSession
    ):
        """Test successful checkout webhook"""
        mock_construct_event.return_value = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123456",
                    "amount_total": 1999,
                    "metadata": {
                        "order_id": "1",
                        "user_id": "1"
                    }
                }
            }
        }
        mock_handle_checkout.return_value = None

        headers = {"stripe-signature": "test_signature"}
        payload = b'{"type": "checkout.session.completed"}'

        with patch("src.config.settings.settings.STRIPE_WEBHOOK_SECRET", "test_secret"):
            response = await async_client.post(
                "/api/v1/stripe/webhook",
                content=payload,
                headers=headers
            )

        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        mock_handle_checkout.assert_called_once()

    @patch("stripe.Webhook.construct_event")
    async def test_stripe_webhook_payment_failed(
            self,
            mock_construct_event: MagicMock,
            async_client: AsyncClient
    ):
        """Test payment failed webhook"""
        mock_construct_event.return_value = {
            "type": "payment_intent.failed",
            "data": {
                "object": {
                    "metadata": {
                        "order_id": "1",
                        "user_id": "1"
                    }
                }
            }
        }

        headers = {"stripe-signature": "test_signature"}
        payload = b'{"type": "payment_intent.failed"}'

        with patch("src.config.settings.settings.STRIPE_WEBHOOK_SECRET", "test_secret"):
            response = await async_client.post(
                "/api/v1/stripe/webhook",
                content=payload,
                headers=headers
            )

        assert response.status_code == 200
        assert response.json() == {"status": "success"}

    @patch("stripe.Webhook.construct_event")
    async def test_stripe_webhook_invalid_signature(
            self,
            mock_construct_event: MagicMock,
            async_client: AsyncClient
    ):
        """Test webhook with invalid signature"""
        mock_construct_event.side_effect = stripe.error.SignatureVerificationError(
            "Invalid signature", "test_signature"
        )

        headers = {"stripe-signature": "invalid_signature"}
        payload = b'{"type": "checkout.session.completed"}'

        with patch("src.config.settings.settings.STRIPE_WEBHOOK_SECRET", "test_secret"):
            response = await async_client.post(
                "/api/v1/stripe/webhook",
                content=payload,
                headers=headers
            )

        assert response.status_code == 400
        assert "Invalid signature" in response.json()["detail"]

    @patch("stripe.Webhook.construct_event")
    async def test_stripe_webhook_invalid_payload(
            self,
            mock_construct_event: MagicMock,
            async_client: AsyncClient
    ):
        """Test webhook with invalid payload"""
        mock_construct_event.side_effect = ValueError("Invalid payload")

        headers = {"stripe-signature": "test_signature"}
        payload = b'invalid_json'

        with patch("src.config.settings.settings.STRIPE_WEBHOOK_SECRET", "test_secret"):
            response = await async_client.post(
                "/api/v1/stripe/webhook",
                content=payload,
                headers=headers
            )

        assert response.status_code == 400
        assert "Invalid payload" in response.json()["detail"]


class TestPaymentModels:
    """Test payment model functionality"""

    async def test_payment_creation(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_order: Order
    ):
        """Test payment model creation"""
        payment = Payment(
            user_id=test_user.id,
            order_id=sample_order.id,
            amount=Decimal("9.99"),
            status=PaymentStatus.successful,
            external_payment_id="cs_test_123456"
        )
        db_session.add(payment)
        await db_session.commit()
        await db_session.refresh(payment)

        assert payment.id is not None
        assert payment.user_id == test_user.id
        assert payment.order_id == sample_order.id
        assert payment.amount == Decimal("9.99")
        assert payment.status == PaymentStatus.successful
        assert payment.external_payment_id == "cs_test_123456"
        assert payment.created_at is not None

    async def test_payment_item_creation(
            self,
            db_session: AsyncSession,
            sample_payment: Payment,
            sample_order: Order
    ):
        """Test payment item creation"""
        order_item_result = await db_session.execute(
            select(OrderItem).where(OrderItem.order_id == sample_order.id)
        )
        order_item = order_item_result.scalar_one()

        payment_item = PaymentItem(
            payment_id=sample_payment.id,
            order_item_id=order_item.id,
            price_at_payment=Decimal("9.99")
        )
        db_session.add(payment_item)
        await db_session.commit()
        await db_session.refresh(payment_item)

        assert payment_item.id is not None
        assert payment_item.payment_id == sample_payment.id
        assert payment_item.order_item_id == order_item.id
        assert payment_item.price_at_payment == Decimal("9.99")

    async def test_payment_relationships(
            self,
            db_session: AsyncSession,
            sample_payment: Payment,
            test_user: User,
            sample_order: Order
    ):
        """Test payment model relationships"""
        payment_result = await db_session.execute(
            select(Payment)
            .where(Payment.id == sample_payment.id)
            .options(
                selectinload(Payment.user),
                selectinload(Payment.order),
                selectinload(Payment.items)
            )
        )
        payment = payment_result.scalar_one()

        assert payment.user.id == test_user.id
        assert payment.order.id == sample_order.id
        assert isinstance(payment.items, list)
