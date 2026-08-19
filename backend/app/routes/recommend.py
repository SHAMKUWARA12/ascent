from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.auth import decode_token

router = APIRouter()

def score_nit_programme(nit, programme, student):

    gate_score = student.get("gate_score", 0)
    category = student.get("category", "UR").upper()

    cat_map = {
        "UR": "UR", "GENERAL": "UR",
        "OBC": "OBC", "OBC-NCL": "OBC",
        "SC": "SC", "ST": "ST", "EWS": "EWS"
    }
    cat_key = cat_map.get(category, "UR")

    # Dummy closing scores per programme per category
    dummy_closing = {
        "NITSLR_CSE": {"UR":600,"OBC":578,"SC":530,"ST":480,"EWS":592},
        "NITSLR_AI":  {"UR":588,"OBC":565,"SC":518,"ST":468,"EWS":580},
        "NITSLR_DS":  {"UR":575,"OBC":552,"SC":505,"ST":455,"EWS":568},
        "NITRK_CSE":  {"UR":645,"OBC":618,"SC":565,"ST":510,"EWS":635},
        "NITRK_AI":   {"UR":632,"OBC":605,"SC":552,"ST":498,"EWS":622},
        "NITT_CSE":   {"UR":658,"OBC":628,"SC":575,"ST":522,"EWS":648},
        "NITT_DS":    {"UR":642,"OBC":612,"SC":560,"ST":508,"EWS":632},
        "NITW_CSE":   {"UR":668,"OBC":638,"SC":585,"ST":532,"EWS":658},
        "NITW_AI":    {"UR":655,"OBC":625,"SC":572,"ST":520,"EWS":645},
        "NITW_DS":    {"UR":645,"OBC":615,"SC":562,"ST":510,"EWS":635},
        "NITC_CSE":   {"UR":638,"OBC":610,"SC":558,"ST":505,"EWS":628},
        "NITC_IT":    {"UR":622,"OBC":595,"SC":542,"ST":490,"EWS":612},
    }

    prog_id = programme.get("program_id", "")
    predicted_closing = dummy_closing.get(prog_id, {}).get(cat_key, 999)

    # Check GATE paper eligibility
    student_paper = student.get("gate_paper", "CS").upper()
    accepted_papers = programme.get("gate_papers", ["CS"])
    if student_paper not in accepted_papers:
        return None  # Not eligible for this programme

    # Probability calculation
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

    # Factor 1: Probability (40pts)
    factor1 = (probability / 100) * 40

    # Factor 2: NIRF ranking (20pts)
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

    # Factor 3: Sentiment (15pts)
    dummy_sentiment = {
        "NITSLR": 7.1,
        "NITRK":  8.1,
        "NITT":   8.3,
        "NITW":   8.4,
        "NITC":   7.9,
    }
    nit_code = nit.get("nit_code", "")
    sentiment = dummy_sentiment.get(nit_code, 6.0)
    factor3 = (sentiment / 10) * 15

    # Factor 4: Location (15pts)
    preferred_region = student.get("preferred_region", "Any")
    nit_region = nit.get("region", "")
    if preferred_region == "Any":
        factor4 = 10
    elif preferred_region.lower() in nit_region.lower():
        factor4 = 15
    else:
        factor4 = 5

    # Factor 5: Branch match (10pts)
    branch_priorities = student.get("branch_priorities", [])
    branch = programme.get("short_name", "")
    factor5 = 0
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

    # Home state bonus
    home_nit = student.get("home_state_nit", "")
    home_bonus = 5 if nit.get("name") == home_nit else 0

    total = factor1 + factor2 + factor3 + factor4 + factor5 + home_bonus

    # Bucket
    if probability >= 80:
        bucket = "Safe"
    elif probability >= 40:
        bucket = "Target"
    else:
        bucket = "Ambitious"

    return {
        "nit_code": nit_code,
        "nit_name": nit.get("name"),
        "programme_id": prog_id,
        "branch": branch,
        "branch_full": programme.get("official_name"),
        "location": nit.get("location"),
        "region": nit.get("region"),
        "nirf_rank": nirf,
        "predicted_closing_score": predicted_closing,
        "your_score": gate_score,
        "category": cat_key,
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


@router.get("/recommend")
async def get_recommendations(token: str):
    db = get_db()

    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email},
        {"_id": 0, "password": 0}
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if not student.get("profile_complete"):
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile first"
        )

    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)

    # Score every NIT × programme combination
    scored = []
    for nit in nits:
        for programme in nit.get("mtech_programs", []):
            result = score_nit_programme(nit, programme, student)
            if result:  # None means not eligible (wrong GATE paper)
                scored.append(result)

    # Sort by total score
    scored.sort(key=lambda x: x["total_score"], reverse=True)

    safe      = [n for n in scored if n["bucket"] == "Safe"]
    target    = [n for n in scored if n["bucket"] == "Target"]
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]

    return {
        "student": {
            "name": student.get("full_name"),
            "gate_score": student.get("gate_score"),
            "category": student.get("category"),
            "domicile": student.get("domicile_state"),
            "gate_paper": student.get("gate_paper")
        },
        "total_eligible": len(scored),
        "safe": safe,
        "target": target,
        "ambitious": ambitious
    }