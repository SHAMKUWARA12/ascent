import statistics
from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.auth import decode_token

router = APIRouter()


async def get_predicted_closing_score(db, institute_code: str,
                                        branch_code: str, category: str):
    """
    Returns (most_recent_year_score, std_dev_across_years, years_of_data).
    Uses ONLY the most recent year's closing score directly —
    NOT an average or weighted estimate. This is a historical
    reference point, not a prediction. A real predictive model
    (Phase 3, trained on full CCMT dataset) will replace this.
    """
    records = await db["ccmt_cutoffs"].find({
        "institute_code": institute_code,
        "branch_code": branch_code,
        "category": category
    }, {"_id": 0}).to_list(length=1000)

    if not records:
        return None, None, 0

    by_year = {}
    for r in records:
        year = r["year"]
        score = r["min_score"]
        if score is None:
            continue
        if year not in by_year or score < by_year[year]:
            by_year[year] = score

    if not by_year:
        return None, None, 0

    most_recent_year = max(by_year.keys())
    reference_score = by_year[most_recent_year]

    scores = list(by_year.values())
    years_available = len(scores)
    std_dev = statistics.pstdev(scores) if len(scores) > 1 else reference_score * 0.08
    std_dev = max(std_dev, 8.0)

    return round(reference_score, 1), round(std_dev, 1), years_available


def probability_from_zscore(gate_score: float, predicted: float, std_dev: float) -> int:
    """
    Converts how far the student's score is from the predicted
    closing score (in standard deviations) into an admission
    probability. This replaces flat +/-offset thresholds and
    properly differentiates Safe/Target/Ambitious based on
    actual historical volatility per NIT+branch+category.
    """
    z = (gate_score - predicted) / std_dev

    if z >= 1.5:
        return 95
    elif z >= 1.0:
        return 85
    elif z >= 0.5:
        return 70
    elif z >= 0.0:
        return 55
    elif z >= -0.5:
        return 40
    elif z >= -1.0:
        return 25
    elif z >= -1.5:
        return 12
    else:
        return 5


async def score_nit_programme(db, nit, programme, student, sentiment_lookup=None):

    gate_score = student.get("gate_score", 0)
    category = student.get("category", "UR").upper()

    cat_map = {
        "UR": "UR", "GENERAL": "UR",
        "OBC": "OBC", "OBC-NCL": "OBC",
        "SC": "SC", "ST": "ST", "EWS": "EWS"
    }
    cat_key = cat_map.get(category, "UR")

    nit_code = nit.get("nit_code", "")
    prog_id = programme.get("program_id", "")
    branch = programme.get("short_name", "")

    predicted_closing, std_dev, years_available = await get_predicted_closing_score(
        db, nit_code, branch, cat_key
    )

    if predicted_closing is None:
        return None  # no historical data for this combination

    # Check GATE paper eligibility
    student_paper = student.get("gate_paper", "CS").upper()
    accepted_papers = programme.get("gate_papers", ["CS"])
    if student_paper not in accepted_papers:
        return None

    probability = probability_from_zscore(gate_score, predicted_closing, std_dev)

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
    if sentiment_lookup and nit_code in sentiment_lookup:
        sentiment = sentiment_lookup[nit_code]
    else:
        sentiment = 6.0
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

    home_nit = student.get("home_state_nit", "")
    home_bonus = 5 if nit.get("name") == home_nit else 0

    total = factor1 + factor2 + factor3 + factor4 + factor5 + home_bonus

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
        # "predicted_closing_score": predicted_closing,
        "reference_closing_score": predicted_closing,
        "reference_year": None,  # optionally track this if you want it shown
        "score_volatility": std_dev,
        "years_of_data": years_available,
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

    sentiment_docs = await db["nit_sentiment"].find({}, {"_id": 0}).to_list(length=100)
    sentiment_lookup = {
        doc["nit_code"]: doc["overall_score"]
        for doc in sentiment_docs
    }

    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)

    scored = []
    for nit in nits:
        for programme in nit.get("mtech_programs", []):
            result = await score_nit_programme(
                db, nit, programme, student, sentiment_lookup
            )
            if result:
                scored.append(result)

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