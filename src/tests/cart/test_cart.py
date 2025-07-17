import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from unittest.mock import patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.movies.models import PurchasedMovie
from src.cart.models import Cart, CartItem
from src.cart.service import add_movie_to_cart, remove_movie_from_cart
from src.users.models import User

from src.tests.movies.conftest import sample_movies
from src.tests.conftest import test_user, async_client
from src.tests.conftest import authenticated_client


class TestAddMovieToCart:
    """Test suite for add_movie_to_cart function"""
    
    async def test_add_movie_to_cart_success(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test successfully adding a movie to cart"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.return_value = None

            with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
                cart = Cart(user_id=test_user.id)
                db_session.add(cart)
                await db_session.commit()
                mock_get_cart.return_value = cart

                await add_movie_to_cart(db_session, test_user, movie.id)

                result = await db_session.execute(
                    select(CartItem).where(
                        CartItem.cart_id == cart.id,
                        CartItem.movie_id == movie.id
                    )
                )
                cart_item = result.scalar_one_or_none()
                assert cart_item is not None
                assert cart_item.cart_id == cart.id
                assert cart_item.movie_id == movie.id

    async def test_add_movie_to_cart_movie_unavailable(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test adding unavailable movie to cart raises exception"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.side_effect = HTTPException(status_code=404, detail="Movie not found")

            with pytest.raises(HTTPException) as exc_info:
                await add_movie_to_cart(db_session, test_user, movie.id)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Movie not found"

    async def test_add_movie_to_cart_already_purchased(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test adding already purchased movie to cart raises exception"""
        movie = sample_movies["movies"][0]

        purchased_movie = PurchasedMovie(user_id=test_user.id, movie_id=movie.id)
        db_session.add(purchased_movie)
        await db_session.commit()

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await add_movie_to_cart(db_session, test_user, movie.id)

            assert exc_info.value.status_code == 400
            assert exc_info.value.detail == "Movie already purchased"

    
    async def test_add_movie_to_cart_already_in_cart(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test adding movie that's already in cart raises exception"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.return_value = None

            with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
                cart = Cart(user_id=test_user.id)
                db_session.add(cart)
                await db_session.commit()

                cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
                db_session.add(cart_item)
                await db_session.commit()

                mock_get_cart.return_value = cart

                with pytest.raises(HTTPException) as exc_info:
                    await add_movie_to_cart(db_session, test_user, movie.id)

                assert exc_info.value.status_code == 400
                assert exc_info.value.detail == "Movie already in cart"

    async def test_add_movie_to_cart_creates_new_cart(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test that cart is created if the user doesn't have one"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.return_value = None

            with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
                new_cart = Cart(user_id=test_user.id)
                db_session.add(new_cart)
                await db_session.commit()
                mock_get_cart.return_value = new_cart

                await add_movie_to_cart(db_session, test_user, movie.id)

                mock_get_cart.assert_called_once_with(db_session, test_user)

                result = await db_session.execute(
                    select(CartItem).where(
                        CartItem.cart_id == new_cart.id,
                        CartItem.movie_id == movie.id
                    )
                )
                cart_item = result.scalar_one_or_none()
                assert cart_item is not None


class TestRemoveMovieFromCart:
    """Test suite for remove_movie_from_cart function"""
    
    async def test_remove_movie_from_cart_success(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test successfully removing a movie from cart"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
            cart = Cart(user_id=test_user.id)
            db_session.add(cart)
            await db_session.commit()

            cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
            db_session.add(cart_item)
            await db_session.commit()

            mock_get_cart.return_value = cart

            await remove_movie_from_cart(db_session, test_user, movie.id)

            result = await db_session.execute(
                select(CartItem).where(
                    CartItem.cart_id == cart.id,
                    CartItem.movie_id == movie.id
                )
            )
            cart_item = result.scalar_one_or_none()
            assert cart_item is None

    async def test_remove_movie_from_cart_not_found(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test removing non-existent movie from cart raises exception"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
            cart = Cart(user_id=test_user.id)
            db_session.add(cart)
            await db_session.commit()

            mock_get_cart.return_value = cart

            with pytest.raises(HTTPException) as exc_info:
                await remove_movie_from_cart(db_session, test_user, movie.id)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Movie not found in cart"

    async def test_remove_movie_from_empty_cart(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test removing movie from empty cart raises exception"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
            cart = Cart(user_id=test_user.id)
            db_session.add(cart)
            await db_session.commit()

            mock_get_cart.return_value = cart

            with pytest.raises(HTTPException) as exc_info:
                await remove_movie_from_cart(db_session, test_user, movie.id)

            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == "Movie not found in cart"


class TestCartEndpoints:
    """Test suite for cart API endpoints"""

    async def test_add_to_cart_endpoint_success(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test successful add to cart endpoint"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.return_value = None

            with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
                cart = Cart(user_id=test_user.id)
                db_session.add(cart)
                await db_session.commit()
                mock_get_cart.return_value = cart

                response = await authenticated_client.post(f"/api/v1/movies/{movie.id}/add")

                assert response.status_code == 200
                assert response.json() == {"detail": "Movie added to cart"}

    async def test_add_to_cart_endpoint_movie_already_purchased(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test add to cart endpoint when movie is already purchased"""
        movie = sample_movies["movies"][0]

        purchased_movie = PurchasedMovie(user_id=test_user.id, movie_id=movie.id)
        db_session.add(purchased_movie)
        await db_session.commit()

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.return_value = None

            response = await authenticated_client.post(f"/api/v1/movies/{movie.id}/add")

            assert response.status_code == 400
            assert response.json() == {"detail": "Movie already purchased"}

    async def test_remove_from_cart_endpoint_success(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test successful remove from cart endpoint"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
            cart = Cart(user_id=test_user.id)
            db_session.add(cart)
            await db_session.commit()

            cart_item = CartItem(cart_id=cart.id, movie_id=movie.id)
            db_session.add(cart_item)
            await db_session.commit()

            mock_get_cart.return_value = cart

            response = await authenticated_client.delete(f"/api/v1/cart/{movie.id}/remove")

            assert response.status_code == 200
            assert response.json() == {"detail": "Movie removed from cart"}

    async def test_remove_from_cart_endpoint_not_found(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test remove from cart endpoint when movie not in cart"""
        movie = sample_movies["movies"][0]

        with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
            cart = Cart(user_id=test_user.id)
            db_session.add(cart)
            await db_session.commit()

            mock_get_cart.return_value = cart

            response = await authenticated_client.delete(f"/api/v1/cart/{movie.id}/remove")

            assert response.status_code == 404
            assert response.json() == {"detail": "Movie not found in cart"}
    
    async def test_add_to_cart_endpoint_unauthorized(self, async_client, sample_movies):
        """Test add to cart endpoint without authentication"""
        movie = sample_movies["movies"][0]

        with patch(
                "src.users.dependencies.get_current_user",
                side_effect=HTTPException(status_code=401, detail="Not authenticated")
        ):
            response = await async_client.post(f"api/v1/movies/{movie.id}/add")

            assert response.status_code == 401
            assert response.json() == {"detail": "Not authenticated"}
    
    async def test_get_user_cart_success(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test successful cart retrieval"""
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        movie1 = sample_movies["movies"][0]
        movie2 = sample_movies["movies"][1]

        item1 = CartItem(cart_id=cart.id, movie_id=movie1.id)
        item2 = CartItem(cart_id=cart.id, movie_id=movie2.id)
        db_session.add_all([item1, item2])
        await db_session.commit()

        response = await authenticated_client.get("/api/v1/cart/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["id"] == movie1.id
        assert data[0]["name"] == movie1.name
        assert data[1]["id"] == movie2.id
        assert data[1]["name"] == movie2.name

    async def test_get_user_cart_empty(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test retrieval of empty cart"""
        response = await authenticated_client.get("/api/v1/cart/")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    async def test_get_user_cart_unauthenticated(
            self,
            async_client: AsyncClient,
            db_session: AsyncSession
    ):
        """Test cart retrieval without authentication"""
        response = await async_client.get("/api/v1/cart/")

        assert response.status_code == 401

    async def test_clear_cart_success(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test successful cart clearing"""
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.commit()
        await db_session.refresh(cart)

        movie1 = sample_movies["movies"][0]
        movie2 = sample_movies["movies"][1]

        item1 = CartItem(cart_id=cart.id, movie_id=movie1.id)
        item2 = CartItem(cart_id=cart.id, movie_id=movie2.id)
        db_session.add_all([item1, item2])
        await db_session.commit()

        response = await authenticated_client.delete("/api/v1/cart/clear")

        assert response.status_code == 200
        assert response.json() == {"detail": "Cart cleared"}

        remaining_items = await db_session.execute(
            select(CartItem).where(CartItem.cart_id == cart.id)
        )
        assert len(remaining_items.scalars().all()) == 0

    async def test_clear_cart_empty_cart(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test clearing an empty cart"""
        response = await authenticated_client.delete("/api/v1/cart/clear")

        assert response.status_code == 200
        assert response.json() == {"detail": "Cart cleared"}

    async def test_clear_cart_unauthenticated(
            self,
            async_client: AsyncClient,
            db_session: AsyncSession
    ):
        """Test clearing cart without authentication"""
        response = await async_client.delete("/api/v1/cart/clear")

        assert response.status_code == 401

    async def test_clear_cart_no_existing_cart(
            self,
            authenticated_client: AsyncClient,
            db_session: AsyncSession,
            test_user: User
    ):
        """Test clearing cart when the user has no cart"""
        response = await authenticated_client.delete("/api/v1/cart/clear")

        assert response.status_code == 200
        assert response.json() == {"detail": "Cart cleared"}

        from sqlalchemy import select
        cart_result = await db_session.execute(
            select(Cart).where(Cart.user_id == test_user.id)
        )
        cart = cart_result.scalar_one_or_none()
        assert cart is not None


class TestIntegrationScenarios:
    """Integration tests for complex cart scenarios"""

    async def test_multiple_movies_cart_operations(
            self,
            db_session: AsyncSession,
            test_user: User,
            sample_movies: dict
    ):
        """Test adding and removing multiple movies from cart"""
        movies = sample_movies["movies"]

        with patch("src.cart.services.check_movie_availability") as mock_check:
            mock_check.return_value = None

            with patch("src.cart.services.get_or_create_cart") as mock_get_cart:
                cart = Cart(user_id=test_user.id)
                db_session.add(cart)
                await db_session.commit()
                mock_get_cart.return_value = cart

                for movie in movies:
                    await add_movie_to_cart(db_session, test_user, movie.id)

                result = await db_session.execute(
                    select(CartItem).where(CartItem.cart_id == cart.id)
                )
                cart_items = result.scalars().all()
                assert len(cart_items) == len(movies)

                await remove_movie_from_cart(db_session, test_user, movies[0].id)

                result = await db_session.execute(
                    select(CartItem).where(CartItem.cart_id == cart.id)
                )
                cart_items = result.scalars().all()
                assert len(cart_items) == len(movies) - 1
                assert cart_items[0].movie_id == movies[1].id
