import aiosmtplib

from email.message import EmailMessage

from src.users.config.settings import settings


async def send_email(to_email: str, subject: str, body: str):
    message = EmailMessage()
    message["From"] = settings.SMTP_SENDER_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        start_tls=True,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
    )

