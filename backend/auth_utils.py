from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os
import smtplib
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

# ✅ Python 3.12 safe
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256"],
    deprecated="auto"
)

# ---------------- PASSWORD UTILS ----------------
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str):
    return pwd_context.verify(password, hashed)

# ---------------- JWT TOKEN ----------------
def create_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ---------------- EMAIL VERIFICATION TOKEN ----------------
def create_email_verification_token(email: str):
    """Create a token for email verification (24-hour expiry)"""
    token = secrets.token_urlsafe(32)
    data = {
        "email": email,
        "token": token,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return token

def verify_email_token(token: str, email: str):
    """Verify that the email token is valid (dummy verification for now)"""
    # In a real scenario, you'd store tokens in DB and validate them
    # For now, return True if token exists
    return token is not None and email is not None

# ---------------- EMAIL SENDING ----------------
def send_verification_email(email: str, verification_link: str):
    """Send email verification link to user"""
    try:
        sender_email = os.getenv("RESET_EMAIL_FROM")
        sender_password = os.getenv("RESET_EMAIL_SMTP_PASS")
        smtp_host = os.getenv("RESET_EMAIL_SMTP_HOST")
        smtp_port = int(os.getenv("RESET_EMAIL_SMTP_PORT", "587"))

        if not sender_email or not sender_password:
            raise Exception("Email credentials not configured in .env")

        # Create email message
        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify Your Email - Interviewr"
        message["From"] = sender_email
        message["To"] = email

        # Plain text version
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

        # HTML version
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

        part1 = MIMEText(text, "plain")
        part2 = MIMEText(html, "html")
        message.attach(part1)
        message.attach(part2)

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, email, message.as_string())

        return True
    except Exception as e:
        print(f"Error sending verification email: {str(e)}")
        return False
