import os
from motor.motor_asyncio import AsyncIOMotorClient

from config import load_backend_env

# ---------------- LOAD ENV ----------------
load_backend_env()

# ---------------- READ MONGO URL ----------------
MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise Exception("MONGO_URL not found in .env file")

# ---------------- CONNECT DB ----------------
client = AsyncIOMotorClient(
    MONGO_URL,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=10000,
)
db = client["apis_db"]

# ---------------- COLLECTIONS ----------------
users_collection = db["users"]
interview_sessions_collection = db["interview_sessions"]
report_ratings_collection = db["report_ratings"]


async def ensure_database_indexes() -> None:
    await users_collection.create_index("email", unique=True, background=True)
    await users_collection.create_index("reset_token", background=True, sparse=True)
    await users_collection.create_index("verification_token", background=True, sparse=True)
    await interview_sessions_collection.create_index("session_id", background=True, sparse=True)
