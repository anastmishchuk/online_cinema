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
    SECRET_KEY: str = os.getenv("SECRET_KEY", "mydefaultsecret")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "mydefaultjwtsecret")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "mydefaultstripekey")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "mydefaultstripehooksecret")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/fastapi_db")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:postgres@db:5432/fastapi_db")

    # Email (for activation and reset password)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.example.com")
    SMTP_PORT: int = os.getenv("SMTP_PORT", 587)
    SMTP_USER: str = os.getenv("SMTP_USER", "user")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "password")
    EMAILS_FROM_EMAIL: EmailStr = os.getenv("EMAILS_FROM_EMAIL", "admin@example.com")
    EMAILS_FROM_NAME: Optional[str] = "Online Cinema Support"

    # Token Expiration
    ACTIVATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 3

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
