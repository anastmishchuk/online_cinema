from fastapi import FastAPI

from users.router import router as users_router

app = FastAPI(
    title="Online Cinema",
    description="Description of project"
)


api_version_prefix = "/api/v1"

app.include_router(users_router, prefix=f"{api_version_prefix}/users", tags=["users"])
