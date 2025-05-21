import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "sandroahobadze@gmail.com"
SMTP_PASS = "xxhj xshz ucyi hqjm"


def send_email(to_email: str, subject: str, body: str):
    message = MIMEMultipart()
    message["From"] = SMTP_USER
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, message.as_string())
        print(f"[INFO] Email sent to {to_email}")
    except Exception as e:
        print(f"[ERROR] Failed to send email to {to_email}: {e}")
