from pydantic import BaseSettings, EmailStr
from typing import Optional


class Settings(BaseSettings):
    # Project
    PROJECT_NAME: str = "Online Cinema"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/onlinecinema"
    SYNC_DATABASE_URL: str = "postgresql://user:password@localhost/db"

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
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
