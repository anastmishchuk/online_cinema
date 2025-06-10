from pydantic_settings import BaseSettings
from pydantic import EmailStr

from typing import Optional


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Online Cinema"
    DEBUG: bool = True

    BASE_URL: str = "http://127.0.0.1:8000"
    API_VERSION_PREFIX: str = "/api/v1"
    USERS_ROUTE_PREFIX: str = "/users"
    PAYMENTS_ROUTE_PREFIX: str = "/payments"

    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

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

    class Config:
        env_file = "src/config/.env"
        env_file_encoding = "utf-8"


settings = Settings()
