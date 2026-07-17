import smtplib
import os
from email.mime.text import MIMEText
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")


def send_reset_email(to_email, reset_token, base_url="http://127.0.0.1:8000"):
    reset_link = f"{base_url}/reset-password?token={reset_token}"

    body = f"""You requested a password reset for your Roota account.

Click the link below to set a new password. This link expires in 1 hour.

{reset_link}

If you didn't request this, you can safely ignore this email."""

    msg = MIMEText(body)
    msg["Subject"] = "Reset your Roota password"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_APP_PASSWORD)
        server.sendmail(SMTP_EMAIL, [to_email], msg.as_string())