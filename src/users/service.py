from src.users.utils.email import send_email


ACTIVATION_TOKEN_EXPIRY_HOURS = 24

async def send_activation_email(to_email: str, token: str):
    link = f"http://localhost:8000/online-cinema/users/activate/{token}"
    subject = "Activate your account"
    body = f"Click the link to activate your account: {link}"
    await send_email(to_email, subject, body)

async def send_reset_password_email(to_email: str, token: str, new_password: str):
    link = f"http://localhost:8000/online-cinema/users/reset-password/{token}?new_password={new_password}"
    subject = "Reset your password"
    body = f"Click the link to reset your password: {link}"
    await send_email(to_email, subject, body)

async def send_password_reset_email(to_email: str, token: str):
    reset_link = f"http://localhost:8000/online-cinema/users/reset-password?token={token}"
    subject = "Reset your password"
    body = f"Click the link to reset your password: {reset_link}"
    await send_email(to_email, subject, body)
