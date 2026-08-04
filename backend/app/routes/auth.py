from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.auth import hash_password, verify_password, create_access_token
from datetime import datetime

router = APIRouter()

# ---------- Request models ----------

class SignupRequest(BaseModel):
    full_name: str
    email: str
    password: str
    gate_paper: str  # CS or DA

class LoginRequest(BaseModel):
    email: str
    password: str

# ---------- Signup ----------

@router.post("/auth/signup")
async def signup(data: SignupRequest):
    db = get_db()

    # Check if email already exists
    existing = await db["students"].find_one({"email": data.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create student document
    student = {
        "full_name": data.full_name,
        "email": data.email,
        "password": hash_password(data.password),
        "gate_paper": data.gate_paper.upper(),
        "profile_complete": False,
        "created_at": datetime.utcnow().isoformat()
    }

    result = await db["students"].insert_one(student)

    # Generate token
    token = create_access_token({
        "sub": data.email,
        "name": data.full_name
    })

    return {
        "message": "Account created successfully",
        "token": token,
        "student": {
            "full_name": data.full_name,
            "email": data.email,
            "gate_paper": data.gate_paper.upper(),
            "profile_complete": False
        }
    }

# ---------- Login ----------

@router.post("/auth/login")
async def login(data: LoginRequest):
    db = get_db()

    # Find student
    student = await db["students"].find_one({"email": data.email})
    if not student:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found"
        )

    # Verify password
    if not verify_password(data.password, student["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )

    # Generate token
    token = create_access_token({
        "sub": student["email"],
        "name": student["full_name"]
    })

    return {
        "message": "Login successful",
        "token": token,
        "student": {
            "full_name": student["full_name"],
            "email": student["email"],
            "gate_paper": student["gate_paper"],
            "profile_complete": student.get("profile_complete", False)
        }
    }

# ---------- Get current student ----------

@router.get("/auth/me")
async def get_me(token: str):
    from app.auth import decode_token
    db = get_db()

    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email},
        {"_id": 0, "password": 0}
    )

    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )

    return student