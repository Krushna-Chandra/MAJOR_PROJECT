from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import os

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
