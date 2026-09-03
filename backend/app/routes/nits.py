from fastapi import APIRouter, HTTPException
from app.database import get_db

router = APIRouter()


@router.get("/nits")
async def get_all_nits():
    db = get_db()
    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)
    return {"total": len(nits), "nits": nits}


@router.get("/nits/{nit_code}")
async def get_nit_detail(nit_code: str):
    """
    Returns full NIT info enriched with real sentiment score,
    so the frontend doesn't need a separate call.
    """
    db = get_db()
    nit = await db["nits"].find_one({"nit_code": nit_code}, {"_id": 0})
    if not nit:
        raise HTTPException(status_code=404, detail="NIT not found")

    sentiment = await db["nit_sentiment"].find_one(
        {"nit_code": nit_code}, {"_id": 0}
    )
    nit["sentiment"] = sentiment  # None if not found

    return nit

ROUND_ORDER = {
    "Round 1": 1, "Round 2": 2, "Round 3": 3,
    "Special Round 1": 4, "Special Round 2": 5,
    "National Spot Round": 6,
}

def round_sort_key(r):
    return (-r["year"], ROUND_ORDER.get(r["round"], 99))

@router.get("/nits/{nit_code}/cutoff-history")
async def get_cutoff_history(nit_code: str, branch: str, category: str = "OBC"):
    """
    Returns REAL round-by-round, year-by-year cutoff scores
    for a specific NIT + branch + category, sourced directly
    from ccmt_cutoffs. Used to populate the round-wise table
    and historical trend on the NIT detail page.
    """
    db = get_db()

    cat_map = {
        "UR": "UR", "GENERAL": "UR",
        "OBC": "OBC", "OBC-NCL": "OBC",
        "SC": "SC", "ST": "ST", "EWS": "EWS"
    }
    cat_key = cat_map.get(category.upper(), category.upper())

    records = await db["ccmt_cutoffs"].find({
        "institute_code": nit_code,
        "branch_code": branch.upper(),
        "category": cat_key
    }, {"_id": 0}).sort([("year", -1)]).to_list(length=500)

    if not records:
        return {
            "nit_code": nit_code,
            "branch": branch,
            "category": cat_key,
            "records": [],
            "message": "No historical data available for this combination"
        }

    # Group by year for the "historical closing score" summary
    # (lowest score per year = that year's FINAL closing score
    # across all rounds — the value used elsewhere as the
    # "closing score (historical)" reference)
    by_year = {}
    for r in records:
        y = r["year"]
        if y not in by_year or r["min_score"] < by_year[y]:
            by_year[y] = r["min_score"]

    return {
        "nit_code": nit_code,
        "branch": branch,
        "category": cat_key,
        "round_wise_records": sorted(records, key=round_sort_key),
        "yearly_final_closing": [
            {"year": y, "closing_score": s}
            for y, s in sorted(by_year.items(), reverse=True)
        ]
    }