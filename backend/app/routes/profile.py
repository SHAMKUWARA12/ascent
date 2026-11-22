from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.auth import decode_token

router = APIRouter()


# ── Request Models ────────────────────────────────────────

class GATEDetails(BaseModel):
    gate_score: float
    gate_year: int
    gate_air: Optional[int] = None
    category: str

class PersonalDetails(BaseModel):
    gender: str
    pwd_status: bool
    domicile_state: str

class BranchPreferences(BaseModel):
    priorities: List[str]
    any_branch: bool = False
    strict_filter: bool = False

class LocationPreferences(BaseModel):
    preferred_region: str
    states_to_avoid: Optional[List[str]] = []

class Constraints(BaseModel):
    risk_appetite: str
    mtech_goal: str
    fee_budget: int
    hostel_needed: bool
    has_backlogs: bool
    btec_cgpa: Optional[float] = None


# ── Save GATE Details ─────────────────────────────────────

@router.post("/profile/gate")
async def save_gate_details(data: GATEDetails, token: str):
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "gate_score": data.gate_score,
            "gate_year":  data.gate_year,
            "gate_air":   data.gate_air,
            "category":   data.category.upper()
        }}
    )
    return {"message": "GATE details saved successfully"}


# ── Save Personal Details ─────────────────────────────────

@router.post("/profile/personal")
async def save_personal_details(data: PersonalDetails, token: str):
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

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
            "gender":         data.gender,
            "pwd_status":     data.pwd_status,
            "domicile_state": data.domicile_state,
            "home_state_nit": home_nit
        }}
    )

    response = {"message": "Personal details saved successfully"}
    if home_nit:
        response["home_state_advantage"] = (
            f"Home state NIT detected: {home_nit}"
        )
    return response


# ── Save Branch Preferences ───────────────────────────────

@router.post("/profile/branches")
async def save_branch_preferences(data: BranchPreferences, token: str):
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "branch_priorities": data.priorities,
            "any_branch":        data.any_branch,
            "strict_filter":     data.strict_filter
        }}
    )
    return {"message": "Branch preferences saved successfully"}


# ── Save Location Preferences ─────────────────────────────

@router.post("/profile/location")
async def save_location_preferences(
    data: LocationPreferences, token: str
):
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "preferred_region": data.preferred_region,
            "states_to_avoid":  data.states_to_avoid
        }}
    )
    return {"message": "Location preferences saved successfully"}


# ── Save Constraints ──────────────────────────────────────

@router.post("/profile/constraints")
async def save_constraints(data: Constraints, token: str):
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "risk_appetite":    data.risk_appetite,
            "mtech_goal":       data.mtech_goal,
            "fee_budget":       data.fee_budget,
            "hostel_needed":    data.hostel_needed,
            "has_backlogs":     data.has_backlogs,
            "btec_cgpa":        data.btec_cgpa,
            "profile_complete": True
        }}
    )
    return {"message": "Profile completed successfully"}


# ── Get Full Profile ──────────────────────────────────────

@router.get("/profile")
async def get_profile(token: str):
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email},
        {"_id": 0, "password": 0}
    )
    if not student:
        raise HTTPException(
            status_code=404, detail="Student not found"
        )
    return student


# ── CV Upload (extract only, not saved yet) ───────────────

@router.post("/profile/cv")
async def upload_cv(token: str, file: UploadFile = File(...)):
    """
    Upload CV PDF and extract B.Tech branch + CGPA.
    Returns extracted data for student to CONFIRM.
    Data is NOT saved to MongoDB until student confirms
    via /profile/cv/confirm endpoint.
    """
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    student = await db["students"].find_one({"email": email})
    if not student:
        raise HTTPException(
            status_code=404, detail="Student not found"
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files accepted"
        )

    pdf_bytes = await file.read()

    if len(pdf_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Max 5MB."
        )

    if len(pdf_bytes) < 1000:
        raise HTTPException(
            status_code=400,
            detail="File too small to be a valid CV."
        )

    from app.cv_extractor import extract_cv_fields
    extracted = extract_cv_fields(pdf_bytes)

    return {
        "extraction_success":  extracted["extraction_success"],
        "btech_branch":        extracted["btech_branch"],
        "btech_cgpa":          extracted["btech_cgpa"],
        "branch_display":      extracted.get("branch_display"),
        "branch_confidence":   extracted["branch_confidence"],
        "cgpa_confidence":     extracted["cgpa_confidence"],
        "needs_confirmation":  True,
        "error":               extracted.get("error"),
        "message": (
            "Please review and confirm the extracted details below."
            if extracted["extraction_success"]
            else (
                extracted.get("error") or
                "Could not extract automatically. "
                "Please fill in manually."
            )
        )
    }


# ── CV Confirm (actually saves to MongoDB) ────────────────

@router.post("/profile/cv/confirm")
async def confirm_cv(
    token: str,
    btech_branch: str,
    btech_cgpa: float,
    confirmed: bool = True,
    use_in_recommendations: bool = True
):
    """
    Student confirms extracted or manually entered CV data.
    confirmed=True means student verified this is their data.
    use_in_recommendations controls whether CV bonus applies.
    """
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    if not confirmed:
        raise HTTPException(
            status_code=400,
            detail="Please confirm the details are correct."
        )

    valid_branches = [
        "CS_IT", "ECE_EE", "MECHANICAL",
        "CIVIL", "CHEMICAL", "OTHER"
    ]
    if btech_branch not in valid_branches:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid branch. Must be one of {valid_branches}"
        )

    if not (0 < btech_cgpa <= 10):
        raise HTTPException(
            status_code=400,
            detail="CGPA must be between 0 and 10"
        )

    from app.cv_extractor import BRANCH_DISPLAY
    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "btech_branch":               btech_branch,
            "btech_branch_display":       BRANCH_DISPLAY.get(
                                            btech_branch, btech_branch
                                          ),
            "btech_cgpa":                 round(btech_cgpa, 2),
            "cv_confirmed":               True,
            "cv_uploaded":                True,
            "use_cv_in_recommendations":  use_in_recommendations,
        }}
    )

    return {
        "success":                True,
        "btech_branch":           btech_branch,
        "btech_cgpa":             round(btech_cgpa, 2),
        "use_in_recommendations": use_in_recommendations,
        "message":                "Academic background saved."
    }


# ── CV Toggle ─────────────────────────────────────────────

@router.post("/profile/cv/toggle")
async def toggle_cv_in_recommendations(
    token: str,
    use_in_recommendations: bool
):
    """Toggle CV bonus on/off without re-uploading."""
    db      = get_db()
    payload = decode_token(token)
    email   = payload.get("sub")

    await db["students"].update_one(
        {"email": email},
        {"$set": {
            "use_cv_in_recommendations": use_in_recommendations
        }}
    )

    return {
        "success":                True,
        "use_in_recommendations": use_in_recommendations,
        "message": (
            "CV background will now affect recommendations."
            if use_in_recommendations
            else "CV background excluded from recommendations."
        )
    }