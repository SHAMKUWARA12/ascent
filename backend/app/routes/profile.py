from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.auth import decode_token

router = APIRouter()

# ---------- Request Models ----------

class GATEDetails(BaseModel):
    gate_score: float
    gate_year: int
    gate_air: Optional[int] = None
    category: str  # UR, OBC, SC, ST, EWS

class PersonalDetails(BaseModel):
    gender: str
    pwd_status: bool
    domicile_state: str

class BranchPreferences(BaseModel):
    priorities: List[str]  # ["CSE", "AI", "DS", "IT"]
    any_branch: bool = False

class LocationPreferences(BaseModel):
    preferred_region: str  # East, West, North, South, Any
    states_to_avoid: Optional[List[str]] = []

class Constraints(BaseModel):
    risk_appetite: str       # Safe, Moderate, Ambitious
    mtech_goal: str          # Industry, Research, Undecided
    fee_budget: int          # annual in rupees
    hostel_needed: bool
    has_backlogs: bool
    btec_cgpa: Optional[float] = None

# ---------- Save GATE Details ----------

@router.post("/profile/gate")
async def save_gate_details(data: GATEDetails, token: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "gate_score": data.gate_score,
            "gate_year": data.gate_year,
            "gate_air": data.gate_air,
            "category": data.category.upper()
        }}
    )
    return {"message": "GATE details saved successfully"}

# ---------- Save Personal Details ----------

@router.post("/profile/personal")
async def save_personal_details(data: PersonalDetails, token: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    # Check home state advantage
    home_state_nits = {
        "Assam": "NIT Silchar",
        "Odisha": "NIT Rourkela",
        "Tamil Nadu": "NIT Trichy",
        "Telangana": "NIT Warangal",
        "Kerala": "NIT Calicut",
        "Karnataka": "NIT Surathkal",
        "Rajasthan": "NIT Jaipur",
        "Madhya Pradesh": "NIT Bhopal",
        "Maharashtra": "NIT Nagpur",
        "Haryana": "NIT Kurukshetra",
    }

    home_nit = home_state_nits.get(data.domicile_state, None)

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "gender": data.gender,
            "pwd_status": data.pwd_status,
            "domicile_state": data.domicile_state,
            "home_state_nit": home_nit
        }}
    )

    response = {"message": "Personal details saved successfully"}
    if home_nit:
        response["home_state_advantage"] = f"Home state NIT detected: {home_nit}"

    return response

# ---------- Save Branch Preferences ----------

@router.post("/profile/branches")
async def save_branch_preferences(data: BranchPreferences, token: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "branch_priorities": data.priorities,
            "any_branch": data.any_branch
        }}
    )
    return {"message": "Branch preferences saved successfully"}

# ---------- Save Location Preferences ----------

@router.post("/profile/location")
async def save_location_preferences(data: LocationPreferences, token: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "preferred_region": data.preferred_region,
            "states_to_avoid": data.states_to_avoid
        }}
    )
    return {"message": "Location preferences saved successfully"}

# ---------- Save Constraints ----------

@router.post("/profile/constraints")
async def save_constraints(data: Constraints, token: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "risk_appetite": data.risk_appetite,
            "mtech_goal": data.mtech_goal,
            "fee_budget": data.fee_budget,
            "hostel_needed": data.hostel_needed,
            "has_backlogs": data.has_backlogs,
            "btec_cgpa": data.btec_cgpa,
            "profile_complete": True
        }}
    )
    return {"message": "Profile completed successfully"}

# ---------- Get Full Profile ----------

@router.get("/profile")
async def get_profile(token: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email},
        {"_id": 0, "password": 0}
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    return student