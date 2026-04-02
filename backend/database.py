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
client = AsyncIOMotorClient(MONGO_URL)
db = client["apis_db"]

# ---------------- COLLECTIONS ----------------
users_collection = db["users"]
