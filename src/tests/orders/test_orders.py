import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch, Mock
from fastapi import HTTPException, status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.orders.models import Order, OrderItem, OrderStatus, RefundRequest, RefundStatus
from src.orders.services import (
    create_order_from_cart,
    get_user_orders,
    revalidate_order_total,
    process_order_payment,
    get_order_by_id
)
from src.cart.models import Cart, CartItem
from src.users.models import User
from src.tests.movies.conftest import sample_movies


class TestOrderServices:
    """Test order services functionality."""

    async def test_create_order_from_cart_success(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test successful order creation from cart."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()

        cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
        db_session.add(cart_item)
        await db_session.commit()

        order = await create_order_from_cart(test_user, db_session)

        assert order.user_id == test_user.id
        assert order.status == OrderStatus.PENDING
        assert order.total_amount == Decimal("9.99")
        assert len(order.items) == 1
        assert order.items[0].movie_id == movie.id
        assert order.items[0].price_at_order == movie.price

        stmt = select(CartItem).where(CartItem.cart_id == cart.id)
        cart_items = (await db_session.execute(stmt)).scalars().all()
        assert len(cart_items) == 0

    async def test_create_order_from_empty_cart(
            self,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test order creation fails with empty cart."""
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await create_order_from_cart(test_user, db_session)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "cart is empty" in exc_info.value.detail

    async def test_create_order_already_purchased_movie(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test order creation fails when a movie is already purchased."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        existing_order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PAID
        )
        db_session.add(existing_order)
        await db_session.commit()

        existing_order_item = OrderItem(
            order_id=existing_order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(existing_order_item)

        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()

        cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
        db_session.add(cart_item)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await create_order_from_cart(test_user, db_session)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already purchased" in exc_info.value.detail

    async def test_create_order_pending_movie_exists(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test order creation fails when movie is already in pending order."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        existing_order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(existing_order)
        await db_session.commit()

        existing_order_item = OrderItem(
            order_id=existing_order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(existing_order_item)

        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()

        cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
        db_session.add(cart_item)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await create_order_from_cart(test_user, db_session)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already pending" in exc_info.value.detail

    async def test_get_user_orders(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test retrieving user orders."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(order_item)
        await db_session.commit()

        orders = await get_user_orders(test_user, db_session)

        assert len(orders) == 1
        assert orders[0].id == order.id
        assert orders[0].user_id == test_user.id
        assert len(orders[0].items) == 1
        assert orders[0].items[0].movie.name.startswith("Action Movie")

    async def test_revalidate_order_total_no_change(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test order total revalidation when no change is needed."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=Decimal("9.99")
        )
        db_session.add(order_item)
        await db_session.commit()

        result = await revalidate_order_total(order, db_session)

        assert result["changed"] is False

    async def test_revalidate_order_total_with_change(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test order total revalidation when change is needed."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=Decimal("11.99")
        )
        db_session.add(order_item)
        await db_session.commit()

        result = await revalidate_order_total(order, db_session)

        assert result["changed"] is True
        assert result["new_total"] == Decimal("11.99")

    @patch("src.orders.services.send_payment_confirmation")
    async def test_process_order_payment_success(
            self,
            mock_send_email: Mock,
            db_session: AsyncSession,
            test_user: User,
    ):
        """Test successful order payment processing."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        mock_send_email.return_value = AsyncMock()

        processed_order = await process_order_payment(order, test_user, db_session)

        assert processed_order.status == OrderStatus.PAID
        mock_send_email.assert_called_once()

    async def test_process_order_payment_wrong_status(
            self,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test order payment processing fails with wrong status."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await process_order_payment(order, test_user, db_session)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "not in pending status" in exc_info.value.detail

    async def test_get_order_by_id_success(
            self,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test successful order retrieval by ID."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        retrieved_order = await get_order_by_id(order.id, test_user.id, db_session)

        assert retrieved_order.id == order.id
        assert retrieved_order.user_id == test_user.id

    async def test_get_order_by_id_not_found(
            self,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test order retrieval fails when order not found."""
        with pytest.raises(Exception) as exc_info:
            await get_order_by_id(999, test_user.id, db_session)

        assert "not found" in str(exc_info.value)


class TestOrderEndpoints:
    """Test order API endpoints."""

    async def test_create_order_endpoint(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test POST /orders/ endpoint."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()

        cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
        db_session.add(cart_item)
        await db_session.commit()

        response = await authenticated_client.post("/api/v1/orders/")

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["status"] == "pending"
        assert data["total_amount"] == "9.99"

    async def test_create_order_empty_cart(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test POST /orders/ with empty cart."""
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()

        response = await authenticated_client.post("/api/v1/orders/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "cart is empty" in response.json()["detail"]

    async def test_list_user_orders(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test GET /orders/ endpoint."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(order_item)
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/orders/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == order.id
        assert data[0]["user_id"] == test_user.id

    async def test_get_order_by_id_endpoint(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test GET /orders/{order_id} endpoint."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(order_item)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/v1/orders/{order.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == order.id
        assert data["user_id"] == test_user.id

    async def test_get_order_not_found(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test GET /orders/{order_id} with non-existent order."""
        response = await authenticated_client.get("/api/v1/orders/999")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    @patch("src.orders.router.create_payment_session")
    async def test_confirm_order_no_price_change(
            self,
            mock_payment: AsyncMock,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test POST /orders/{order_id}/confirm with no price change."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=Decimal("9.99")
        )
        db_session.add(order_item)
        await db_session.commit()

        mock_payment.return_value = AsyncMock()
        mock_payment.return_value.checkout_url = "https://payment.example.com/checkout"

        response = await authenticated_client.post(f"/api/v1/orders/{order.id}/confirm")

        assert response.status_code == status.HTTP_303_SEE_OTHER
        mock_payment.assert_called_once()

    @patch("src.orders.router.create_payment_session")
    @patch("src.orders.router.revalidate_order_total")
    async def test_confirm_order_price_change(
            self,
            mock_revalidate: AsyncMock,
            mock_payment: AsyncMock,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test POST /orders/{order_id}/confirm with price change."""
        movie = sample_movies["movies"][0]
        movie.price = Decimal("15.99")
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=Decimal("9.99")
        )
        db_session.add(order_item)
        await db_session.commit()

        mock_revalidate.return_value = {
            "changed": True,
            "new_total": Decimal("15.99")
        }

        response = await authenticated_client.post(f"/api/v1/orders/{order.id}/confirm")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "warning" in data
        assert "15.99" in data["warning"]
        assert "order" in data
        assert data["order"]["id"] == order.id
        assert len(data["order"]["items"]) == 1

        mock_payment.assert_not_called()

    async def test_confirm_order_not_found(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test POST /orders/{order_id}/confirm with non-existent order."""
        response = await authenticated_client.post("/api/v1/orders/999/confirm")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]

    async def test_cancel_order_success(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test POST /orders/{order_id}/cancel/ endpoint."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        response = await authenticated_client.post(f"/api/v1/orders/{order.id}/cancel/")

        assert response.status_code == status.HTTP_200_OK
        assert "canceled" in response.json()["detail"]

        await db_session.refresh(order)
        assert order.status == OrderStatus.CANCELED

    async def test_cancel_already_canceled_order(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test canceling already canceled order."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.CANCELED
        )
        db_session.add(order)
        await db_session.commit()

        response = await authenticated_client.post(f"/api/v1/orders/{order.id}/cancel/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already canceled" in response.json()["detail"]

    async def test_cancel_paid_order(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test canceling paid order."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()

        response = await authenticated_client.post(f"/api/v1/orders/{order.id}/cancel/")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "request a refund" in response.json()["detail"]

    async def test_request_refund_success(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test POST /orders/{order_id}/refund endpoint."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()

        refund_data = {
            "reason": "Product not as described"
        }

        response = await authenticated_client.post(
            f"/api/v1/orders/{order.id}/refund",
            json=refund_data
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert "submitted successfully" in response.json()["detail"]

        stmt = select(RefundRequest).where(RefundRequest.order_id == order.id)
        refund = (await db_session.execute(stmt)).scalar_one_or_none()
        assert refund is not None
        assert refund.reason == "Product not as described"
        assert refund.status == RefundStatus.PENDING

    async def test_request_refund_non_paid_order(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test refund request for non-paid order."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PENDING
        )
        db_session.add(order)
        await db_session.commit()

        refund_data = {
            "reason": "Product not as described"
        }

        response = await authenticated_client.post(
            f"/api/v1/orders/{order.id}/refund",
            json=refund_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Only paid orders" in response.json()["detail"]

    async def test_request_refund_duplicate(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test duplicate refund request."""
        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("19.99"),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()

        existing_refund = RefundRequest(
            user_id=test_user.id,
            order_id=order.id,
            reason="First refund"
        )
        db_session.add(existing_refund)
        await db_session.commit()

        refund_data = {
            "reason": "Second refund attempt"
        }

        response = await authenticated_client.post(
            f"/api/v1/orders/{order.id}/refund",
            json=refund_data
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already submitted" in response.json()["detail"]

    async def test_request_refund_order_not_found(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test refund request for non-existent order."""
        refund_data = {
            "reason": "Product not as described"
        }

        response = await authenticated_client.post(
            "/api/v1/orders/999/refund",
            json=refund_data
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]


class TestOrderIntegration:
    """Integration tests for order workflow."""

    async def test_complete_order_workflow(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test complete order workflow from cart to payment."""
        movie1 = sample_movies["movies"][0]
        movie2 = sample_movies["movies"][1]
        db_session.add_all([movie1, movie2])

        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()

        cart_item1 = CartItem(cart_id=cart.id, movie_id=movie1.id)
        cart_item2 = CartItem(cart_id=cart.id, movie_id=movie2.id)
        db_session.add_all([cart_item1, cart_item2])
        await db_session.commit()

        response = await authenticated_client.post("/api/v1/orders/")
        assert response.status_code == status.HTTP_201_CREATED
        order_data = response.json()
        order_id = order_data["id"]
        assert order_data["total_amount"] == "20.98"

        response = await authenticated_client.get(f"/api/v1/orders/{order_id}")
        assert response.status_code == status.HTTP_200_OK
        order_data = response.json()
        assert len(order_data["items"]) == 2

        response = await authenticated_client.get("/api/v1/orders/")
        assert response.status_code == status.HTTP_200_OK
        orders = response.json()
        assert len(orders) == 1
        assert orders[0]["id"] == order_id

        response = await authenticated_client.post(f"/api/v1/orders/{order_id}/cancel/")
        assert response.status_code == status.HTTP_200_OK

        response = await authenticated_client.get(f"/api/v1/orders/{order_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "canceled"

    async def test_refund_workflow(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test refund request workflow."""
        movie = sample_movies["movies"][0]
        db_session.add(movie)

        order = Order(
            user_id=test_user.id,
            total_amount=Decimal("9.99"),
            status=OrderStatus.PAID
        )
        db_session.add(order)
        await db_session.commit()

        order_item = OrderItem(
            order_id=order.id,
            movie_id=movie.id,
            price_at_order=movie.price
        )
        db_session.add(order_item)
        await db_session.commit()

        refund_data = {"reason": "Product not as described"}
        response = await authenticated_client.post(
            f"/api/v1/orders/{order.id}/refund",
            json=refund_data
        )

        assert response.status_code == status.HTTP_201_CREATED

        stmt = select(RefundRequest).where(RefundRequest.order_id == order.id)
        refund = (await db_session.execute(stmt)).scalar_one_or_none()
        assert refund is not None
        assert refund.reason == "Product not as described"
        assert refund.status == RefundStatus.PENDING
        assert refund.processed is False
