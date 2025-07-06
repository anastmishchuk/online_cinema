import os

from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import EmailStr, ConfigDict

from typing import Optional


load_dotenv()

class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Online Cinema"
    DEBUG: bool = True

    BASE_URL: str = "http://127.0.0.1:8000"
    API_VERSION_PREFIX: str = "/api/v1"
    USERS_ROUTE_PREFIX: str = "/users"
    AUTH_ROUTE_PREFIX: str = "/auth"
    PAYMENTS_ROUTE_PREFIX: str = "/payment"

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/online_cinema"
    SYNC_DATABASE_URL: str = "postgresql://user:password@localhost:5432/online_cinema"

    # Email (for activation and reset password)
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAILS_FROM_EMAIL: EmailStr
    EMAILS_FROM_NAME: Optional[str] = "Online Cinema Support"


    # Token Expiration
    ACTIVATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 3

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    model_config = ConfigDict(
        env_file="src/config/.env",
        env_file_encoding="utf-8"
    )


settings = Settings()
