from fastapi import Request, FastAPI
from markupsafe import Markup
from sqladmin import Admin, ModelView

from src.admin.admin_service import check_admin_access
from src.cart.models import Cart
from src.config.database import engine
from src.movies.models import Movie
from src.users.models import User, UserGroup


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
        return check_admin_access(request)


class UserGroupAdmin(ModelView, model=UserGroup):
    column_list = [UserGroup.id, UserGroup.name]
    can_edit = True
    can_create = True
    can_delete = False

    async def is_accessible(self, request: Request) -> bool:
        return check_admin_access(request)


class MovieAdmin(ModelView, model=Movie):
    column_list = [
        Movie.id,
        Movie.name,
        "year",
        "imdb",
        "price",
        "genres_list",
        "directors_list",
        "stars_list",
        "short_description",
    ]

    column_labels = {
        "id": "ID",
        "name": "Title",
        "year": "Year",
        "imdb": "IMDb",
        "price": "Price",
        "genres_list": "Genres",
        "directors_list": "Directors",
        "stars_list": "Stars",
        "short_description": "Description",
    }

    column_searchable_list = [Movie.name, Movie.description]
    column_sortable_list = [Movie.id, Movie.name, Movie.year, Movie.imdb, Movie.price]

    can_create = True
    can_edit = True
    can_delete = True

    column_formatters = {
        "genres_list": lambda v, m, n: v._list_names(m.genres),
        "directors_list": lambda v, m, n: v._list_names(m.directors),
        "stars_list": lambda v, m, n: v._list_names(m.stars),
        "short_description": lambda v, m, n: Markup(m.description[:100] + "...")
        if m.description else "—",
    }

    def _list_names(self, items) -> str:
        if not items:
            return "—"
        return ", ".join([item.name for item in items])

    async def is_accessible(self, request: Request) -> bool:
        return check_admin_access(request)

class CartAdmin(ModelView, model=Cart):
    column_list = [Cart.id, "user_id", "movies"]
    column_labels = {
        "id": "Cart ID",
        "user_id": "User ID",
        "movies": "Movies in Cart",
    }

    can_create = False
    can_edit = False
    can_delete = True

    column_formatters = {
        "movies": lambda admin, request, cart, *args: admin.movies(request, cart),
    }

    def movies(self, request: Request, cart: Cart) -> str:
        items = cart.cart_items or []
        if not items:
            return "—"

        links = []
        for item in items:
            movie = item.movie
            if movie:
                url = get_admin_url(request, "movie", "detail", movie.id)
                link = f'<a href="{url}" target="_blank">{movie.name}</a>'
                links.append(link)

        return Markup("<br>".join(links)) if links else "—"

    async def is_accessible(self, request: Request) -> bool:
        return check_admin_access(request)


def setup_admin(app, engine):
    admin = Admin(app, engine)

    admin.add_view(UserAdmin)
    admin.add_view(UserGroupAdmin)
    admin.add_view(MovieAdmin)
    admin.add_view(CartAdmin)
    # admin.add_view(OrderAdmin)
    # admin.add_view(PaymentAdmin)
