from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os
import smtplib
import requests
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets

from config import load_backend_env

# ---------------- LOAD ENV ---------------
load_backend_env()

# ---------------- CONSTANTS ----------------
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise Exception("SECRET_KEY not found in .env file")

pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_email_verification_token(email: str):
    token = secrets.token_urlsafe(32)
    data = {
        "email": email,
        "token": token,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return token


def verify_email_token(token: str, email: str):
    return token is not None and email is not None


def _normalize_smtp_password(password: str) -> str:
    return "".join((password or "").split())


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value.strip()
    return default


def get_email_provider_settings() -> dict:
    resend_api_key = _first_env("RESEND_API_KEY")
    resend_from = _first_env("RESEND_FROM_EMAIL", "EMAIL_FROM", "MAIL_FROM", "RESET_EMAIL_FROM")
    resend_reply_to = _first_env("RESEND_REPLY_TO", "EMAIL_REPLY_TO", default=resend_from)
    return {
        "provider": "resend" if resend_api_key and resend_from else "smtp",
        "resend_api_key": resend_api_key,
        "resend_from": resend_from,
        "resend_reply_to": resend_reply_to,
    }


def get_email_settings() -> dict:
    provider_settings = get_email_provider_settings()
    sender_email = _first_env("RESET_EMAIL_FROM", "SMTP_FROM", "EMAIL_FROM", "MAIL_FROM")
    smtp_host = _first_env("RESET_EMAIL_SMTP_HOST", "SMTP_HOST", "EMAIL_SMTP_HOST", "MAIL_HOST")
    smtp_port = int(_first_env("RESET_EMAIL_SMTP_PORT", "SMTP_PORT", "EMAIL_SMTP_PORT", "MAIL_PORT", default="587"))
    smtp_user = _first_env("RESET_EMAIL_SMTP_USER", "SMTP_USER", "EMAIL_SMTP_USER", "MAIL_USERNAME", default=sender_email)
    smtp_password = _normalize_smtp_password(
        _first_env("RESET_EMAIL_SMTP_PASS", "SMTP_PASS", "EMAIL_SMTP_PASS", "MAIL_PASSWORD")
    )
    return {
        "provider": provider_settings["provider"],
        "resend_api_key": provider_settings["resend_api_key"],
        "resend_from": provider_settings["resend_from"],
        "resend_reply_to": provider_settings["resend_reply_to"],
        "sender_email": sender_email,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
        "smtp_user": smtp_user,
        "smtp_password": smtp_password,
    }


def get_email_config_status() -> dict:
    settings = get_email_settings()
    provider = settings["provider"]
    sender = settings["resend_from"] if provider == "resend" else settings["sender_email"]
    smtp_user = settings["smtp_user"]
    resend_reply_to = settings["resend_reply_to"]
    return {
        "provider": provider,
        "configured": (
            bool(settings["resend_api_key"] and settings["resend_from"])
            if provider == "resend"
            else bool(settings["sender_email"] and settings["smtp_host"] and settings["smtp_password"])
        ),
        "has_resend_api_key": bool(settings["resend_api_key"]),
        "has_resend_from": bool(settings["resend_from"]),
        "has_resend_reply_to": bool(resend_reply_to),
        "smtp_host": settings["smtp_host"],
        "smtp_port": settings["smtp_port"],
        "from_domain": sender.split("@", 1)[1] if "@" in sender else "",
        "smtp_user_matches_from": bool(sender and smtp_user and sender.lower() == smtp_user.lower()),
        "has_sender": bool(settings["sender_email"]),
        "has_smtp_user": bool(settings["smtp_user"]),
        "has_smtp_password": bool(settings["smtp_password"]),
    }


def _send_smtp_message(message, recipient_email: str) -> None:
    settings = get_email_settings()
    sender_email = settings["sender_email"]
    smtp_host = settings["smtp_host"]
    smtp_port = settings["smtp_port"]
    smtp_user = settings["smtp_user"] or sender_email
    sender_password = settings["smtp_password"]

    if not sender_email or not smtp_host or not sender_password:
        raise RuntimeError("Email SMTP configuration is incomplete")

    message["From"] = sender_email
    message["To"] = recipient_email

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20) as server:
            server.login(smtp_user, sender_password)
            server.send_message(message)
        return

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, sender_password)
        server.send_message(message)


def _send_resend_email(
    recipient_email: str,
    subject: str,
    html: str = "",
    text: str = "",
) -> None:
    settings = get_email_settings()
    resend_api_key = settings["resend_api_key"]
    sender_email = settings["resend_from"]
    reply_to = settings["resend_reply_to"]

    if not resend_api_key or not sender_email:
        raise RuntimeError("Resend configuration is incomplete")

    payload = {
        "from": sender_email,
        "to": [recipient_email],
        "subject": subject,
    }
    if html:
        payload["html"] = html
    if text or html:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=15,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Resend send failed: {response.status_code} {response.text}")


def _send_email(
    recipient_email: str,
    subject: str,
    html: str = "",
    text: str = "",
) -> None:
    settings = get_email_settings()
    if settings["provider"] == "resend":
        _send_resend_email(recipient_email, subject, html=html, text=text)
        return

    if html:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        if text:
            message.attach(MIMEText(text, "plain"))
        message.attach(MIMEText(html, "html"))
    else:
        message = EmailMessage()
        message["Subject"] = subject
        message.set_content(text)
    _send_smtp_message(message, recipient_email)


def get_frontend_base_url() -> str:
    return _first_env(
        "REACT_APP_FRONTEND_BASE",
        "RESET_EMAIL_BASE_URL",
        "FRONTEND_BASE_URL",
        "PUBLIC_FRONTEND_URL",
        default="http://localhost:3000",
    ).rstrip("/")


def send_verification_email(email: str, verification_link: str):
    try:
        text = f"""\
        Hi there,

        Thank you for signing up with Interviewr!

        Please verify your email address by clicking the link below:
        {verification_link}

        This link will expire in 24 hours.

        If you didn't create this account, you can ignore this email.

        Best regards,
        Interviewr Team
        """

        html = f"""\
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #333; margin-bottom: 20px;">Verify Your Email</h2>
                    <p style="color: #666; font-size: 16px; line-height: 1.5;">
                        Hi there,<br><br>
                        Thank you for signing up with <strong>Interviewr</strong>!<br><br>
                        Please verify your email address by clicking the button below:
                    </p>
                    <div style="margin: 30px 0; text-align: center;">
                        <a href="{verification_link}" style="display: inline-block; background-color: #007bff; color: white; padding: 12px 40px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                            Verify Email
                        </a>
                    </div>
                    <p style="color: #999; font-size: 14px;">
                        Or copy and paste this link: {verification_link}
                    </p>
                    <p style="color: #999; font-size: 14px; margin-top: 20px;">
                        This link will expire in 24 hours.
                    </p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="color: #999; font-size: 12px;">
                        If you didn't create this account, you can ignore this email.
                    </p>
                    <p style="color: #999; font-size: 12px; margin-top: 10px;">
                        Best regards,<br>
                        <strong>Interviewr Team</strong>
                    </p>
                </div>
            </body>
        </html>
        """
        _send_email(
            email,
            "Verify Your Email - Interviewr",
            html=html,
            text=text,
        )
        return True
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False


def send_reset_email(to_email: str, token: str) -> None:
    reset_link = f"{get_frontend_base_url()}/reset-password?token={token}"
    text = (
        "You requested a password reset for INTERVIEWR.\n\n"
        f"Reset link: {reset_link}\n\n"
        "This link is valid for 5 minutes.\n\n"
        "If you did not request this, you can ignore this email."
    )
    html = f"""\
    <html>
        <body style="font-family: Arial, sans-serif; background-color: #f5f5f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #333; margin-bottom: 20px;">Reset Your Password</h2>
                <p style="color: #666; font-size: 16px; line-height: 1.5;">
                    You requested a password reset for <strong>INTERVIEWR</strong>.
                </p>
                <div style="margin: 30px 0; text-align: center;">
                    <a href="{reset_link}" style="display: inline-block; background-color: #007bff; color: white; padding: 12px 40px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Reset Password
                    </a>
                </div>
                <p style="color: #999; font-size: 14px;">
                    Or copy and paste this link: {reset_link}
                </p>
                <p style="color: #999; font-size: 14px; margin-top: 20px;">
                    This link is valid for 5 minutes.
                </p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="color: #999; font-size: 12px;">
                    If you did not request this, you can ignore this email.
                </p>
            </div>
        </body>
    </html>
    """
    _send_email(
        to_email,
        "Reset your INTERVIEWR password",
        html=html,
        text=text,
    )
