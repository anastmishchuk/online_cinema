from src.config.settings import settings
from src.users.utils.email import send_email


async def send_activation_email(to_email: str, token: str):
    link = (f"{settings.BASE_URL}"
            f"{settings.API_VERSION_PREFIX}"
            f"{settings.USERS_ROUTE_PREFIX}/activate/{token}")
    subject = "Activate your account"
    body = f"Click the link to activate your account: {link}"
    await send_email(to_email, subject, body)


async def send_reset_password_email(to_email: str, token: str, new_password: str):
    link = (f"{settings.BASE_URL}"
            f"{settings.API_VERSION_PREFIX}"
            f"{settings.USERS_ROUTE_PREFIX}/reset-password/"
            f"{token}?new_password={new_password}")
    subject = "Reset your password"
    body = f"Click the link to reset your password: {link}"
    await send_email(to_email, subject, body)


async def send_password_reset_email(to_email: str, token: str):
    reset_link = (f"{settings.BASE_URL}"
                  f"{settings.API_VERSION_PREFIX}"
                  f"{settings.USERS_ROUTE_PREFIX}/reset-password?token={token}")
    subject = "Reset your password"
    body = f"Click the link to reset your password: {reset_link}"
    await send_email(to_email, subject, body)
