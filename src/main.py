from fastapi import FastAPI

from admin.admin import admin_app, setup_admin
from config.database import engine
from users.router import router as users_router
from users.auth.router import router as auth_router

from movies.router.movies import router as movies_router
from movies.router.genres import router as genres_router
from movies.router.stars import router as stars_router
from cart.router import router as cart_router
from orders.router import router as orders_router
from payment.router import router as payment_router
from payment.webhooker_router import router as stripe_router


app = FastAPI(
    title="Online Cinema",
    description="A digital platform that allows users to select, watch, "
                "and purchase access to movies and other video materials via the internet"
)

api_version_prefix = "/api/v1"

setup_admin(app, engine)

app.mount("/admin", admin_app)

app.include_router(
    users_router,
    prefix=f"{api_version_prefix}/users",
    tags=["users"]
)

app.include_router(
    auth_router,
    prefix=f"{api_version_prefix}/auth",
    tags=["auth"]
)

app.include_router(
    movies_router,
    prefix=f"{api_version_prefix}/movies",
    tags=["movies"]
)

app.include_router(
    genres_router,
    prefix=f"{api_version_prefix}/genres",
    tags=["genres"]
)

app.include_router(
    stars_router,
    prefix=f"{api_version_prefix}/stars",
    tags=["stars"]
)

app.include_router(
    cart_router,
    prefix=f"{api_version_prefix}/cart",
    tags=["cart"]
)

app.include_router(
    orders_router,
    prefix=f"{api_version_prefix}/orders",
    tags=["orders"]
)

app.include_router(
    payment_router,
    prefix=f"{api_version_prefix}/payment",
    tags=["payment"]
)

app.include_router(
    stripe_router,
    prefix=f"{api_version_prefix}/stripe",
    tags=["stripe"]
)
