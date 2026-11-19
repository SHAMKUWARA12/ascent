from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.auth import decode_token
from fastapi import APIRouter, HTTPException, UploadFile, File

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
    strict_filter: bool = False

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
        "Andhra Pradesh":   "NIT Andhra Pradesh",
        "Assam":            "NIT Silchar",
        "Bihar":            "NIT Patna",
        "Chhattisgarh":     "NIT Raipur",
        "Delhi":            "NIT Delhi",
        "Goa":              "NIT Goa",
        "Gujarat":          "NIT Surat",
        "Haryana":          "NIT Kurukshetra",
        "Himachal Pradesh": "NIT Hamirpur",
        "Jharkhand":        "NIT Jamshedpur",
        "Karnataka":        "NIT Surathkal",
        "Kerala":           "NIT Calicut",
        "Madhya Pradesh":   "NIT Bhopal",
        "Maharashtra":      "NIT Nagpur",
        "Manipur":          "NIT Manipur",
        "Meghalaya":        "NIT Meghalaya",
        "Mizoram":          "NIT Mizoram",
        "Nagaland":         "NIT Nagaland",
        "Odisha":           "NIT Rourkela",
        "Punjab":           "NIT Jalandhar",
        "Rajasthan":        "NIT Jaipur",
        "Sikkim":           "NIT Sikkim",
        "Tamil Nadu":       "NIT Trichy",
        "Telangana":        "NIT Warangal",
        "Tripura":          "NIT Agartala",
        "Uttar Pradesh":    "NIT Allahabad",
        "Uttarakhand":      "NIT Uttarakhand",
        "West Bengal":      "NIT Durgapur",
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
            "any_branch": data.any_branch,
            "strict_filter": data.strict_filter
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

# ---------- Student CV ----------

@router.post("/profile/cv")
async def upload_cv(token: str, file: UploadFile = File(...)):
    """
    Upload student CV PDF and extract B.Tech branch + CGPA.
    Stores extracted data in student MongoDB document.
    """
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    student = await db["students"].find_one({"email": email})
    if not student:
        raise HTTPException(
            status_code=404, detail="Student not found"
        )

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted"
        )

    # Read file bytes
    pdf_bytes = await file.read()

    if len(pdf_bytes) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 5MB."
        )

    # Extract CV fields
    from app.cv_extractor import extract_cv_fields
    extracted = extract_cv_fields(pdf_bytes)

    # Store in MongoDB
    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "btech_branch":          extracted["btech_branch"],
            "btech_cgpa":            extracted["btech_cgpa"],
            "cv_branch_confidence":  extracted["branch_confidence"],
            "cv_cgpa_confidence":    extracted["cgpa_confidence"],
            "cv_uploaded":           True,
            "cv_extraction_success": extracted["extraction_success"],
        }}
    )

    return {
        "success":          True,
        "btech_branch":     extracted["btech_branch"],
        "btech_cgpa":       extracted["btech_cgpa"],
        "branch_confidence": extracted["branch_confidence"],
        "cgpa_confidence":  extracted["cgpa_confidence"],
        "extraction_success": extracted["extraction_success"],
        "message":          (
            f"Extracted: Branch={extracted['btech_branch']}, "
            f"CGPA={extracted['btech_cgpa']}"
            if extracted["extraction_success"]
            else "Could not extract data. "
                 "Please fill in manually."
        ),
        "error": extracted.get("error")
    }


@router.post("/profile/cv-manual")
async def set_cv_manual(
    token: str,
    btech_branch: str = "CS_IT",
    btech_cgpa: float = 8.0
):
    """
    Manual fallback if CV extraction fails.
    Student can type their branch and CGPA directly.
    """
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    valid_branches = [
        "CS_IT", "ECE_EE", "MECHANICAL",
        "CIVIL", "CHEMICAL", "OTHER"
    ]
    if btech_branch not in valid_branches:
        raise HTTPException(
            status_code=400,
            detail=f"Branch must be one of {valid_branches}"
        )

    if not 0 < btech_cgpa <= 10:
        raise HTTPException(
            status_code=400,
            detail="CGPA must be between 0 and 10"
        )

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "btech_branch":   btech_branch,
            "btech_cgpa":     btech_cgpa,
            "cv_uploaded":    False,
            "cv_manual_entry": True,
        }}
    )

    return {
        "success":      True,
        "btech_branch": btech_branch,
        "btech_cgpa":   btech_cgpa
    }