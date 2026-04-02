import os
from datetime import datetime, timezone
import numpy as np
from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Header,
    Body
)
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError
from bson import ObjectId
from deepface import DeepFace

from database import users_collection
from auth_utils import (
    hash_password,
    verify_password,
    create_token,
    SECRET_KEY,
    ALGORITHM
)
from interview_ai import (
    ProviderError,
    complete_interview_session,
    create_interview_session,
    evaluate_interview_answer,
    get_ai_provider_status,
    get_session_payload,
)

app = FastAPI()

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- DIRECTORIES ----------------
UPLOAD_DIR = "uploads"
FACE_DB = "face_db"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(FACE_DB, exist_ok=True)

# ---------------- FACE EMBEDDING ----------------
def get_embedding(image_path):
    try:
        emb = DeepFace.represent(
            img_path=image_path,
            model_name="Facenet",
            enforce_detection=True
        )
        return np.array(emb[0]["embedding"])
    except Exception:
        return None

# ---------------- AUTH HELPER ----------------
async def get_current_user(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await users_collection.find_one(
            {"_id": ObjectId(user_id)}
        )
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ================= REGISTER =================
@app.post("/register")
async def register(
    first_name: str = Body(...),
    last_name: str = Body(...),
    email: str = Body(...),
    password: str = Body(...)
):
    if not first_name.strip() or not last_name.strip():
        raise HTTPException(
            status_code=400,
            detail="First name and last name required"
        )

    existing = await users_collection.find_one({"email": email})
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    user = {
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "email": email,
        "hashed_password": hash_password(password),
        "profile_image": None
    }

    result = await users_collection.insert_one(user)

    return {
        "status": "USER REGISTERED",
        "id": str(result.inserted_id)
    }

# ================= LOGIN =================
@app.post("/login")
async def login(
    email: str = Body(...),
    password: str = Body(...)
):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=400,
            detail="User not found"
        )

    if not verify_password(password, user["hashed_password"]):
        raise HTTPException(
            status_code=400,
            detail="Invalid password"
        )

    token = create_token({
        "user_id": str(user["_id"]),
        "email": user["email"]
    })

    return {
        "access_token": token,
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "profile_image": user.get("profile_image")
        }
    }

# ================= REGISTER FACE =================
# functionality removed per requirements - endpoint disabled
# @app.post("/register-face")
# async def register_face(
#     file: UploadFile = File(...),
#     authorization: str = Header(...)
# ):
#     token = authorization.replace("Bearer ", "")
#     user = await get_current_user(token)
#
#     img_path = os.path.join(
#         UPLOAD_DIR,
#         f"user_{user['_id']}.jpg"
#     )
#     with open(img_path, "wb") as f:
#         f.write(await file.read())
#
#     embedding = get_embedding(img_path)
#     if embedding is None:
#         return {"status": "FACE NOT DETECTED"}
#
#     np.save(
#         os.path.join(
#             FACE_DB,
#             f"user_{user['_id']}.npy"
#         ),
#         embedding
#     )
#
#     return {"status": "FACE REGISTERED"}

# ================= FACE LOGIN =================
# functionality removed per requirements - endpoint disabled
# @app.post("/login-face")
# async def login_face(
#     file: UploadFile = File(...)
# ):
#     img_path = os.path.join(UPLOAD_DIR, "login.jpg")
#     with open(img_path, "wb") as f:
#         f.write(await file.read())
#
#     new_embedding = get_embedding(img_path)
#     if new_embedding is None:
#         return {"status": "FACE NOT DETECTED"}
#
#     best_user = None
#     best_distance = float("inf")
#
#     for fname in os.listdir(FACE_DB):
#         if fname.endswith(".npy"):
#             uid = fname.replace("user_", "").replace(".npy", "")
#             saved_embedding = np.load(
#                 os.path.join(FACE_DB, fname)
#             )


# ================= PROFILE =================
@app.get("/profile")
async def get_profile(
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token)

    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "profile_image": user.get("profile_image")
    }

@app.put("/profile")
async def update_profile(
    first_name: str = Body(None),
    last_name: str = Body(None),
    profile_image: str = Body(None),
    authorization: str = Header(...)
):
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token)

    update_data = {}

    if first_name is not None:
        first_name = first_name.strip()
        if first_name != "":
            update_data["first_name"] = first_name

    if last_name is not None:
        last_name = last_name.strip()
        if last_name != "":
            update_data["last_name"] = last_name


    if profile_image is not None:
            if profile_image == "":
                update_data["profile_image"] =None
            else:
                update_data["profile_image"] = profile_image

    if update_data:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": update_data}
        )

    updated_user = await users_collection.find_one(
        {"_id": user["_id"]}
    )

    return {
        "status": "PROFILE UPDATED",
        "user": {
            "id": str(updated_user["_id"]),
            "email": updated_user["email"],
            "first_name": updated_user.get("first_name"),
            "last_name": updated_user.get("last_name"),
            "profile_image": updated_user.get("profile_image")
        }
    }

# ================= INTERVIEW RESULTS =================
@app.post("/interview-result")
async def save_interview_result(
    user_id: str = Body(...),
    category: str = Body(...),
    score: int = Body(...),
    transcript: str = Body(...),
    questions_answered: int = Body(...),
    authorization: str = Header(...)
):
    """Save interview result to database"""
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)

        interview_result = {
            "user_id": user_id,
            "category": category,
            "score": score,
            "transcript": transcript,
            "questions_answered": questions_answered,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        result = await users_collection.update_one(
            {"_id": current_user["_id"]},
            {
                "$push": {
                    "interview_results": interview_result
                }
            }
        )

        return {
            "status": "INTERVIEW RESULT SAVED",
            "score": score,
            "category": category
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save interview result: {str(e)}"
        )


# ================= AI INTERVIEW =================
@app.post("/ai-interview/start")
async def start_ai_interview(
    payload: dict = Body(...),
    authorization: str = Header(None)
):
    try:
        user = None
        if authorization:
            token = authorization.replace("Bearer ", "")
            user = await get_current_user(token)

        session = await create_interview_session(
            {
                **payload,
                "user_id": str(user["_id"]) if user else None,
            }
        )
        return session
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to start interview: {exc}")


@app.get("/ai-interview/providers/status")
async def ai_provider_status():
    try:
        return get_ai_provider_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to inspect AI providers: {exc}")


@app.post("/ai-interview/evaluate")
async def evaluate_ai_interview_answer(
    session_id: str = Body(...),
    question_index: int = Body(...),
    answer: str = Body(...),
):
    try:
        return await evaluate_interview_answer(session_id, question_index, answer)
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answer: {exc}")


@app.post("/ai-interview/complete")
async def complete_ai_interview(
    session_id: str = Body(...),
    ended_early: bool = Body(False),
    authorization: str = Header(None)
):
    try:
        summary = await complete_interview_session(session_id, ended_early=ended_early)
        session = get_session_payload(session_id)
        current_user = None

        if authorization and session:
            token = authorization.replace("Bearer ", "")
            current_user = await get_current_user(token)

            interview_result = {
                "session_id": session_id,
                "category": session.get("context", {}).get("category") or "general",
                "selected_mode": session.get("context", {}).get("selected_mode"),
                "job_role": session.get("context", {}).get("job_role"),
                "primary_language": session.get("context", {}).get("primary_language"),
                "experience": session.get("context", {}).get("experience"),
                "context": session.get("context", {}),
                "score": summary.get("overall_score", 0),
                "ended_early": summary.get("ended_early", False),
                "summary": summary.get("summary"),
                "top_strengths": summary.get("top_strengths", []),
                "improvement_areas": summary.get("improvement_areas", []),
                "strongest_questions": summary.get("strongest_questions", []),
                "needs_work_questions": summary.get("needs_work_questions", []),
                "providers": summary.get("providers"),
                "answers": session.get("answers", []),
                "evaluations": session.get("evaluations", []),
                "questions_answered": len(session.get("evaluations", [])),
                "total_questions": len(session.get("questions", [])),
                "question_outline": session.get("question_outline", summary.get("questions", [])),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await users_collection.update_one(
                {"_id": current_user["_id"]},
                {"$push": {"interview_results": interview_result}},
            )

        return {
            **summary,
            "context": session.get("context", {}) if session else {},
            "answers": session.get("answers", []) if session else [],
            "evaluations": session.get("evaluations", []) if session else [],
            "questions_answered": len(session.get("evaluations", [])) if session else 0,
            "question_outline": session.get("question_outline", []) if session else [],
            "user": (
                {
                    "id": str(current_user["_id"]),
                    "email": current_user.get("email"),
                    "first_name": current_user.get("first_name"),
                    "last_name": current_user.get("last_name"),
                }
                if current_user
                else None
            ),
        }
    except ProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to complete interview: {exc}")


@app.get("/interview-reports")
async def get_interview_reports(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)
        reports = current_user.get("interview_results", [])
        normalized_reports = list(reversed(reports))
        return {"reports": normalized_reports}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch interview reports: {exc}")


@app.get("/interview-reports/{session_id}")
async def get_interview_report(session_id: str, authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        current_user = await get_current_user(token)
        reports = current_user.get("interview_results", [])
        match = next((item for item in reports if item.get("session_id") == session_id), None)

        if not match:
            raise HTTPException(status_code=404, detail="Interview report not found")

        return {"report": match}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch interview report: {exc}")

