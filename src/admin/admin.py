from fastapi import Request, FastAPI
from sqladmin import Admin, ModelView

from cart.models import Cart, CartItem
from config.database import engine
from orders.models import Order, RefundRequest, OrderItem
from payment.models import Payment, PaymentItem
from users.models import User, UserGroup, UserProfile
from movies.models import (
    Movie,
    Genre,
    Star,
    Director,
    Certification,
    Like,
    MovieRating,
    Comment,
    PurchasedMovie
)
from .admin_service import check_admin_access, check_admin_or_moderator_access


admin_app = FastAPI()

admin = Admin(admin_app, engine)


def get_admin_url(request: Request, admin_name: str, action: str, obj_id: int) -> str:
    return request.url_for(f"admin:{admin_name}-{action}", id=obj_id)


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.email, User.is_active, User.group_id, User.created_at]
    column_searchable_list = [User.email]
    column_filters = [User.is_active, User.group_id]
    can_create = False
    can_delete = True
    can_edit = True

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class UserGroupAdmin(ModelView, model=UserGroup):
    column_list = [UserGroup.id, UserGroup.name]
    can_edit = True
    can_create = True
    can_delete = False

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class UserProfileAdmin(ModelView, model=UserProfile):
    column_list = [UserProfile.id,
                   UserProfile.user_id,
                   UserProfile.first_name,
                   UserProfile.last_name,
                   UserProfile.date_of_birth,
                   UserProfile.info]
    can_edit = True
    can_create = False
    can_delete = False

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class MovieAdmin(ModelView, model=Movie):
    column_list = [
        Movie.id, Movie.name, Movie.year, Movie.time,
        Movie.imdb, Movie.votes, Movie.price, Movie.certification_id
    ]
    column_searchable_list = [Movie.name, Movie.description]
    column_filters = [Movie.year, Movie.certification_id, Movie.imdb]
    column_sortable_list = [Movie.id, Movie.name, Movie.year, Movie.imdb, Movie.votes]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 25
    page_size_options = [25, 50, 100]

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class GenreAdmin(ModelView, model=Genre):
    column_list = [Genre.id, Genre.name]
    column_searchable_list = [Genre.name]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class StarAdmin(ModelView, model=Star):
    column_list = [Star.id, Star.name]
    column_searchable_list = [Star.name]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class DirectorAdmin(ModelView, model=Director):
    column_list = [Director.id, Director.name]
    column_searchable_list = [Director.name]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class CertificationAdmin(ModelView, model=Certification):
    column_list = [Certification.id, Certification.name]
    column_searchable_list = [Certification.name]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class LikeAdmin(ModelView, model=Like):
    column_list = [Like.id, Like.user_id, Like.target_type, Like.target_id, Like.is_like]
    column_filters = [Like.target_type, Like.is_like]
    column_sortable_list = [Like.id, Like.user_id, Like.target_type, Like.target_id]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class MovieRatingAdmin(ModelView, model=MovieRating):
    column_list = [MovieRating.id, MovieRating.user_id, MovieRating.movie_id, MovieRating.rating]
    column_filters = [MovieRating.rating]
    column_sortable_list = [MovieRating.id, MovieRating.user_id, MovieRating.movie_id, MovieRating.rating]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class CommentAdmin(ModelView, model=Comment):
    column_list = [Comment.id, Comment.user_id, Comment.movie_id, Comment.parent_id, Comment.created_at]
    column_searchable_list = [Comment.text]
    column_filters = [Comment.movie_id, Comment.parent_id]
    column_sortable_list = [Comment.id, Comment.user_id, Comment.movie_id, Comment.created_at]

    can_create = False
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_or_moderator_access(request)


class PurchasedMovieAdmin(ModelView, model=PurchasedMovie):
    column_list = [
        PurchasedMovie.id,
        PurchasedMovie.user_id,
        PurchasedMovie.movie_id,
        PurchasedMovie.purchased_at,
        PurchasedMovie.payment_id,
    ]
    column_filters = [
        PurchasedMovie.purchased_at,
        PurchasedMovie.payment_id,
    ]
    column_sortable_list = [
        PurchasedMovie.id,
        PurchasedMovie.user_id,
        PurchasedMovie.movie_id,
        PurchasedMovie.purchased_at
    ]

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class CartAdmin(ModelView, model=Cart):
    column_list = [Cart.id, Cart.user_id]
    column_filters = [Cart.user_id]

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class CartItemAdmin(ModelView, model=CartItem):
    column_list = [
        CartItem.id,
        CartItem.cart_id,
        CartItem.movie_id,
        CartItem.added_at
    ]
    column_filters = [
        CartItem.cart_id,
        CartItem.movie_id,
        CartItem.added_at,
    ]
    column_sortable_list = [
        CartItem.id,
        CartItem.cart_id,
        CartItem.movie_id,
        CartItem.added_at
    ]

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class OrderAdmin(ModelView, model=Order):
    column_list = [
        Order.id,
        Order.user_id,
        Order.status,
        Order.total_amount,
        Order.created_at,
        Order.items
    ]
    column_filters = [Order.status, Order.created_at, Order.total_amount]
    column_sortable_list = [
        Order.id,
        Order.user_id,
        Order.status,
        Order.total_amount,
        Order.created_at
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 50
    page_size_options = [25, 50, 100]

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class OrderItemAdmin(ModelView, model=OrderItem):
    column_list = [
        OrderItem.id,
        OrderItem.order_id,
        OrderItem.movie_id,
        OrderItem.price_at_order
    ]
    column_filters = [
        OrderItem.order_id,
        OrderItem.movie_id,
        OrderItem.price_at_order,
    ]
    column_sortable_list = [
        OrderItem.id,
        OrderItem.order_id,
        OrderItem.movie_id,
        OrderItem.price_at_order
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class RefundRequestAdmin(ModelView, model=RefundRequest):
    column_list = [
        RefundRequest.id,
        RefundRequest.user_id,
        RefundRequest.order_id,
        RefundRequest.status,
        RefundRequest.created_at,
        RefundRequest.processed
    ]
    column_searchable_list = [RefundRequest.reason]
    column_filters = [
        RefundRequest.status,
        RefundRequest.processed,
        RefundRequest.created_at,
        RefundRequest.user_id,
        RefundRequest.order_id
    ]
    column_sortable_list = [
        RefundRequest.id,
        RefundRequest.user_id,
        RefundRequest.order_id,
        RefundRequest.status,
        RefundRequest.created_at
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class PaymentAdmin(ModelView, model=Payment):
    column_list = [
        Payment.id,
        Payment.user_id,
        Payment.order_id,
        Payment.status,
        Payment.amount,
        Payment.items,
        Payment.created_at,
        Payment.external_payment_id
    ]
    column_searchable_list = [Payment.external_payment_id]
    column_filters = [
        Payment.status,
        Payment.created_at,
        Payment.amount,
        Payment.user_id,
        Payment.order_id
    ]
    column_sortable_list = [
        Payment.id,
        Payment.user_id,
        Payment.order_id,
        Payment.status,
        Payment.amount,
        Payment.created_at
    ]

    can_create = False
    can_edit = True
    can_delete = False
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


class PaymentItemAdmin(ModelView, model=PaymentItem):
    column_list = [
        PaymentItem.id,
        PaymentItem.payment_id,
        PaymentItem.order_item_id,
        PaymentItem.price_at_payment
    ]
    column_filters = [
        PaymentItem.payment_id,
        PaymentItem.order_item_id,
        PaymentItem.price_at_payment,
    ]
    column_sortable_list = [
        PaymentItem.id,
        PaymentItem.payment_id,
        PaymentItem.order_item_id,
        PaymentItem.price_at_payment
    ]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    page_size = 50

    async def is_accessible(self, request: Request) -> bool:
        return await check_admin_access(request)


def setup_admin(app, engine):
    admin = Admin(app, engine)

    admin.add_view(UserAdmin)
    admin.add_view(UserGroupAdmin)
    admin.add_view(UserProfileAdmin)

    admin.add_view(MovieAdmin)
    admin.add_view(GenreAdmin)
    admin.add_view(StarAdmin)
    admin.add_view(DirectorAdmin)
    admin.add_view(CertificationAdmin)
    admin.add_view(LikeAdmin)
    admin.add_view(MovieRatingAdmin)
    admin.add_view(CommentAdmin)
    admin.add_view(PurchasedMovieAdmin)

    admin.add_view(CartAdmin)
    admin.add_view(CartItemAdmin)

    admin.add_view(OrderAdmin)
    admin.add_view(OrderItemAdmin)
    admin.add_view(RefundRequestAdmin)

    admin.add_view(PaymentAdmin)
    admin.add_view(PaymentItemAdmin)

    return admin
