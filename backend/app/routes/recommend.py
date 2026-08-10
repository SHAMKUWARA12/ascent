from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.auth import decode_token

router = APIRouter()

# ---------- Helper: Score a NIT ----------

def score_nit(nit, student):

    total = 0

    # --- Factor 1: Admission Probability (40 points) ---
    gate_score = student.get("gate_score", 0)
    category = student.get("category", "UR").upper()

    # Map category to seat key
    cat_map = {
        "UR": "UR", "GENERAL": "UR",
        "OBC": "OBC", "OBC-NCL": "OBC",
        "SC": "SC", "ST": "ST", "EWS": "EWS"
    }
    cat_key = cat_map.get(category, "UR")

    # Get predicted closing score for this NIT
    # Using dummy scores for now
    # Will be replaced by ML model later
    dummy_closing = {
        "NITSLR": {"UR": 620, "OBC": 590, "SC": 540, "ST": 490, "EWS": 610},
        "NITRK":  {"UR": 670, "OBC": 635, "SC": 580, "ST": 530, "EWS": 655},
        "NITT":   {"UR": 680, "OBC": 645, "SC": 590, "ST": 540, "EWS": 665},
        "NITW":   {"UR": 690, "OBC": 655, "SC": 600, "ST": 550, "EWS": 675},
        "NITC":   {"UR": 660, "OBC": 625, "SC": 570, "ST": 520, "EWS": 645},
    }

    nit_code = nit.get("nit_code", "")
    predicted_closing = dummy_closing.get(nit_code, {}).get(cat_key, 999)

    # Calculate probability
    if gate_score >= predicted_closing + 20:
        probability = 95
    elif gate_score >= predicted_closing:
        probability = 70
    elif gate_score >= predicted_closing - 15:
        probability = 45
    elif gate_score >= predicted_closing - 30:
        probability = 25
    else:
        probability = 5

    factor1 = (probability / 100) * 40
    total += factor1

    # --- Factor 2: NIRF Ranking (20 points) ---
    nirf = nit.get("nirf_rank", 50)
    if nirf <= 10:
        factor2 = 20
    elif nirf <= 20:
        factor2 = 16
    elif nirf <= 30:
        factor2 = 12
    elif nirf <= 50:
        factor2 = 8
    else:
        factor2 = 4
    total += factor2

    # --- Factor 3: Sentiment Score (15 points) ---
    # Dummy sentiment scores for now
    # Will be replaced by real Reddit/PaGaLGuY data later
    dummy_sentiment = {
        "NITSLR": 7.1,
        "NITRK":  8.1,
        "NITT":   8.3,
        "NITW":   8.4,
        "NITC":   7.9,
    }
    sentiment = dummy_sentiment.get(nit_code, 6.0)
    factor3 = (sentiment / 10) * 15
    total += factor3

    # --- Factor 4: Location Match (15 points) ---
    preferred_region = student.get("preferred_region", "Any")
    nit_region = nit.get("region", "")

    if preferred_region == "Any":
        factor4 = 10
    elif preferred_region.lower() in nit_region.lower():
        factor4 = 15
    else:
        factor4 = 5
    total += factor4

    # --- Factor 5: Branch Match (10 points) ---
    branch_priorities = student.get("branch_priorities", [])
    nit_branches = [
        p.get("short_name", "")
        for p in nit.get("mtech_programs", [])
    ]

    factor5 = 0
    for branch in nit_branches:
        if branch in branch_priorities:
            idx = branch_priorities.index(branch)
            if idx == 0:
                factor5 = 10
            elif idx == 1:
                factor5 = 8
            elif idx == 2:
                factor5 = 6
            else:
                factor5 = 4
            break
    total += factor5

    # --- Home State Bonus ---
    home_nit = student.get("home_state_nit", "")
    home_bonus = 5 if nit.get("name") == home_nit else 0
    total += home_bonus

    # --- Category bucket ---
    if probability >= 80:
        bucket = "Safe"
    elif probability >= 40:
        bucket = "Target"
    else:
        bucket = "Ambitious"

    return {
        "nit_code": nit_code,
        "nit_name": nit.get("name"),
        "location": nit.get("location"),
        "region": nit.get("region"),
        "nirf_rank": nirf,
        "predicted_closing_score": predicted_closing,
        "your_score": gate_score,
        "admission_probability": probability,
        "sentiment_score": sentiment,
        "total_score": round(total, 1),
        "bucket": bucket,
        "home_state": nit.get("name") == home_nit,
        "score_breakdown": {
            "probability_factor": round(factor1, 1),
            "nirf_factor": round(factor2, 1),
            "sentiment_factor": round(factor3, 1),
            "location_factor": round(factor4, 1),
            "branch_factor": round(factor5, 1),
            "home_bonus": home_bonus
        }
    }


# ---------- Main Recommendation Endpoint ----------

@router.get("/recommend")
async def get_recommendations(token: str):
    db = get_db()

    # Get student profile
    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email},
        {"_id": 0, "password": 0}
    )

    if not student:
        raise HTTPException(
            status_code=404,
            detail="Student not found"
        )

    if not student.get("profile_complete"):
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile first"
        )

    # Get all NITs
    nits = await db["nits"].find(
        {},
        {"_id": 0}
    ).to_list(length=100)

    # Score every NIT
    scored = [score_nit(nit, student) for nit in nits]

    # Sort by total score
    scored.sort(key=lambda x: x["total_score"], reverse=True)

    # Split into buckets
    safe = [n for n in scored if n["bucket"] == "Safe"]
    target = [n for n in scored if n["bucket"] == "Target"]
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]

    return {
        "student": {
            "name": student.get("full_name"),
            "gate_score": student.get("gate_score"),
            "category": student.get("category"),
            "domicile": student.get("domicile_state")
        },
        "total_eligible": len(scored),
        "safe": safe,
        "target": target,
        "ambitious": ambitious
    }