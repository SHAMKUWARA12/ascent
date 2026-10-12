from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.auth import decode_token

router = APIRouter()


async def get_scored_nits(student, db):
    from app.routes.recommend import score_nit_programme

    nits = await db["nits"].find(
        {}, {"_id": 0}
    ).to_list(length=100)

    sentiment_docs = await db["nit_sentiment"].find(
        {}, {"_id": 0}
    ).to_list(length=100)
    sentiment_lookup = {
        doc["nit_code"]: doc["overall_score"]
        for doc in sentiment_docs
    }

    scored = []
    for nit in nits:
        for programme in nit.get("mtech_programs", []):
            result = await score_nit_programme(
                db, nit, programme, student, sentiment_lookup
            )
            if result:
                scored.append(result)

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


def generate_preference_list(scored: list) -> list:
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]
    target    = [n for n in scored if n["bucket"] == "Target"]
    safe      = [n for n in scored if n["bucket"] == "Safe"]

    ordered = ambitious + target + safe

    preferences = []
    for i, nit in enumerate(ordered, 1):
        nirf_display = nit.get("nirf_rank_display") or (
            f"#{nit['nirf_rank']}" if nit.get("nirf_rank")
            else "Band 101+"
        )
        preferences.append({
            "preference_no":     i,
            "nit_code":          nit["nit_code"],
            "nit_name":          nit["nit_name"],
            "branch":            nit["branch"],
            "branch_full":       nit.get("branch_full", ""),
            "category":          nit["category"],
            "probability":       nit["admission_probability"],
            "bucket":            nit["bucket"],
            "total_score":       nit["total_score"],
            "nirf_rank":         nit.get("nirf_rank"),
            "nirf_display":      nirf_display,
            "predicted_closing": nit.get("predicted_closing_score"),
        })

    return preferences


@router.get("/choice-filing/part1")
async def get_choice_filing_part1(token: str):
    db = get_db()

    payload = decode_token(token)
    email   = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email}, {"_id": 0, "password": 0}
    )
    if not student:
        raise HTTPException(
            status_code=404, detail="Student not found"
        )
    if not student.get("profile_complete"):
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile first"
        )

    scored      = await get_scored_nits(student, db)
    preferences = generate_preference_list(scored)

    return {
        "part":        "Part 1 — Regular Rounds (R1, R2, R3)",
        "description": (
            "Submit this list on the CCMT portal before "
            "Round 1 opens. The same list is valid for all "
            "three regular rounds. Ambitious choices are "
            "listed first — CCMT allots your highest eligible "
            "preference automatically."
        ),
        "total":       len(preferences),
        "preferences": preferences
    }


@router.post("/choice-filing/part2")
async def get_choice_filing_part2(
    token: str,
    current_allocation: str = "No seat"
):
    db = get_db()

    payload = decode_token(token)
    email   = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email}, {"_id": 0, "password": 0}
    )
    if not student:
        raise HTTPException(
            status_code=404, detail="Student not found"
        )

    got_seat = (
        current_allocation.strip().lower() not in
        ["no seat", "no", "none", ""]
    )

    if not got_seat:
        scored      = await get_scored_nits(student, db)
        preferences = generate_preference_list(scored)
        return {
            "part":               "Part 2 — Special Rounds (SR1, SR2)",
            "current_allocation": None,
            "got_seat":           False,
            "description":        (
                "You did not receive a seat in regular rounds. "
                "Submit this fresh list for Special Rounds."
            ),
            "total":              len(preferences),
            "preferences":        preferences
        }

    scored      = await get_scored_nits(student, db)
    upgrade     = [
        n for n in scored
        if n["nit_name"] not in current_allocation
        or n["branch"] not in current_allocation
    ]
    preferences = generate_preference_list(upgrade)

    return {
        "part":               "Part 2 — Special Rounds (SR1, SR2)",
        "current_allocation": current_allocation,
        "got_seat":           True,
        "description":        (
            "You have a current seat. This list focuses on "
            "upgrade options. Your current seat is safe — "
            "FLOAT and SLIDE are risk-free choices."
        ),
        "total":              len(preferences),
        "preferences":        preferences
    }


@router.post("/advisor")
async def advisor(
    token: str,
    current_nit: str    = "",
    current_branch: str = "",
    target_nit: str     = "",
    target_branch: str  = "Any"
):
    db = get_db()

    payload = decode_token(token)
    email   = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email}, {"_id": 0, "password": 0}
    )
    if not student:
        raise HTTPException(
            status_code=404, detail="Student not found"
        )

    if not current_nit or not current_branch or not target_nit:
        raise HTTPException(
            status_code=400,
            detail="Please provide current NIT, branch, and target NIT"
        )

    nits = await db["nits"].find(
        {}, {"_id": 0}
    ).to_list(length=100)

    sentiment_docs = await db["nit_sentiment"].find(
        {}, {"_id": 0}
    ).to_list(length=100)
    sentiment_lookup = {
        doc["nit_code"]: doc["overall_score"]
        for doc in sentiment_docs
    }

    current_nit_doc = None
    target_nit_doc  = None

    for nit in nits:
        name_lower = nit.get("name", "").lower()
        code_lower = nit.get("nit_code", "").lower()

        if (name_lower == current_nit.strip().lower() or
                code_lower == current_nit.strip().lower()):
            current_nit_doc = nit

        if (name_lower == target_nit.strip().lower() or
                code_lower == target_nit.strip().lower()):
            target_nit_doc = nit

    if not current_nit_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Current NIT '{current_nit}' not found"
        )
    if not target_nit_doc:
        raise HTTPException(
            status_code=404,
            detail=f"Target NIT '{target_nit}' not found"
        )

    # Sort ranks — always integers 1-31 (lower = better NIT)
    current_nirf_sort = current_nit_doc.get("nirf_rank_sort") or 31
    target_nirf_sort  = target_nit_doc.get("nirf_rank_sort")  or 31

    # Display ranks — may be None for band NITs
    current_nirf = current_nit_doc.get("nirf_rank")
    target_nirf  = target_nit_doc.get("nirf_rank")

    current_nirf_display = (
        f"#{current_nirf}" if current_nirf
        else current_nit_doc.get("nirf_rank_display", "Band 101+")
    )
    target_nirf_display = (
        f"#{target_nirf}" if target_nirf
        else target_nit_doc.get("nirf_rank_display", "Band 101+")
    )

    branch_priorities = student.get("branch_priorities", [])

    def pref_index(branch):
        try:
            return branch_priorities.index(branch.upper())
        except ValueError:
            return 999

    current_pref_idx = pref_index(current_branch)
    target_pref_idx  = (
        pref_index(target_branch)
        if target_branch and target_branch.lower() != "any"
        else 999
    )

    same_nit    = (current_nit.strip().lower() ==
                   target_nit.strip().lower())
    same_branch = (current_branch.strip().upper() ==
                   target_branch.strip().upper())

    # Compute probability of getting target
    from app.routes.recommend import (
        get_predicted_closing_score,
        probability_from_zscore
    )

    cat_map = {
        "UR": "UR", "GENERAL": "UR",
        "OBC": "OBC", "OBC-NCL": "OBC",
        "SC": "SC", "ST": "ST", "EWS": "EWS"
    }
    cat_key    = cat_map.get(
        student.get("category", "UR").upper(), "UR"
    )
    gate_score = student.get("gate_score", 0)

    target_branch_for_calc = (
        target_branch
        if target_branch and target_branch.lower() != "any"
        else current_branch
    )
    target_nit_code = target_nit_doc.get("nit_code", "")

    predicted, std_dev, years = await get_predicted_closing_score(
        db, target_nit_code, target_branch_for_calc, cat_key
    )

    probability = (
        probability_from_zscore(gate_score, predicted, std_dev)
        if predicted is not None else 50
    )

    # Also get preference list so we can find current
    # allocation's position in the student's list
    scored      = await get_scored_nits(student, db)
    preferences = generate_preference_list(scored)

    # Find what preference number matches current allocation
    current_pref_no = None
    target_pref_no  = None
    for p in preferences:
        if (p["nit_name"].lower() == current_nit.strip().lower()
                and p["branch"].upper() == current_branch.strip().upper()):
            current_pref_no = p["preference_no"]
        if (p["nit_name"].lower() == target_nit.strip().lower()
                and p["branch"].upper() ==
                target_branch.strip().upper()):
            target_pref_no = p["preference_no"]

    # Preferences BETTER than current allocation
    # (lower preference number = higher priority = better)
    better_preferences = []
    if current_pref_no:
        better_preferences = [
            p for p in preferences
            if p["preference_no"] < current_pref_no
        ]

    # ── SAME SEAT ───────────────────────────────────────────
    if same_nit and same_branch:
        return {
            "recommendation":       "FREEZE",
            "risk_level":           "NONE",
            "reason":               (
                f"You selected the same seat you currently have "
                f"({current_nit} — {current_branch}). "
                f"FREEZE to confirm this seat permanently."
            ),
            "current_nirf_display": current_nirf_display,
            "target_nirf_display":  target_nirf_display,
            "probability":          100,
            "current_pref_no":      current_pref_no,
            "target_pref_no":       target_pref_no,
            "better_preferences":   better_preferences,
            "all_options":          _all_options_explanation()
        }

    # ── SAME NIT ─────────────────────────────────────────────
    if same_nit:
        if target_pref_idx < current_pref_idx:
            recommendation = "SLIDE"
            risk_level     = "NONE"
            reason = (
                f"You want a better branch at {current_nit}. "
                f"SLIDE is completely safe — if {target_branch} "
                f"cutoff is too high you automatically keep "
                f"{current_branch}. "
                f"Probability of getting {target_branch}: {probability}%."
            )
        else:
            recommendation = "FREEZE"
            risk_level     = "NONE"
            reason = (
                f"Your current branch ({current_branch}) is already "
                f"equal or higher priority than {target_branch} at "
                f"{current_nit}. FREEZE to confirm your current seat."
            )
        return {
            "recommendation":       recommendation,
            "risk_level":           risk_level,
            "reason":               reason,
            "probability":          probability,
            "current_nit":          current_nit,
            "current_branch":       current_branch,
            "current_nirf_display": current_nirf_display,
            "current_nirf_sort":    current_nirf_sort,
            "target_nit":           target_nit,
            "target_branch":        target_branch,
            "target_nirf_display":  target_nirf_display,
            "target_nirf_sort":     target_nirf_sort,
            "predicted_closing":    predicted,
            "years_of_data":        years,
            "current_pref_no":      current_pref_no,
            "target_pref_no":       target_pref_no,
            "better_preferences":   better_preferences,
            "all_options":          _all_options_explanation()
        }

    # ── DIFFERENT NIT ─────────────────────────────────────────
    # FIX: target NIT must be strictly better ranked (lower sort
    # number) to recommend FLOAT. Branch preference alone is NOT
    # enough to justify moving to a worse-ranked NIT.
    target_is_strictly_better_nit = (
        target_nirf_sort < current_nirf_sort
    )

    # Target preference number must be lower (higher priority)
    # than current in the generated list
    target_is_better_in_list = (
        target_pref_no is not None and
        current_pref_no is not None and
        target_pref_no < current_pref_no
    )

    if target_is_strictly_better_nit or target_is_better_in_list:
        recommendation = "FLOAT"
        risk_level     = "NONE"
        reason = (
            f"Your target ({target_nit} — {target_branch}, "
            f"NIRF {target_nirf_display}) is ranked higher than "
            f"your current seat ({current_nit} — {current_branch}, "
            f"NIRF {current_nirf_display}). "
            f"FLOAT is completely safe — if you don't get "
            f"{target_nit} you automatically keep "
            f"{current_nit} — {current_branch}. "
            f"Probability of getting target: {probability}%."
        )
    else:
        recommendation = "FREEZE"
        risk_level     = "NONE"
        reason = (
            f"Your current seat ({current_nit} — {current_branch}, "
            f"NIRF {current_nirf_display}) is already better than "
            f"your target ({target_nit} — {target_branch}, "
            f"NIRF {target_nirf_display}). "
            f"There is no benefit to floating toward a lower-ranked "
            f"NIT. FREEZE to confirm your current seat permanently."
        )

    return {
        "recommendation":       recommendation,
        "risk_level":           risk_level,
        "reason":               reason,
        "probability":          probability,
        "current_nit":          current_nit,
        "current_branch":       current_branch,
        "current_nirf_display": current_nirf_display,
        "current_nirf_sort":    current_nirf_sort,
        "target_nit":           target_nit,
        "target_branch":        target_branch,
        "target_nirf_display":  target_nirf_display,
        "target_nirf_sort":     target_nirf_sort,
        "predicted_closing":    predicted,
        "years_of_data":        years,
        "current_pref_no":      current_pref_no,
        "target_pref_no":       target_pref_no,
        "better_preferences":   better_preferences,
        "all_options":          _all_options_explanation()
    }


def _all_options_explanation():
    return {
        "FREEZE": {
            "title":      "FREEZE — Confirm Current Seat",
            "definition": (
                "You are satisfied with your current allotment. "
                "Not considered for better choices in subsequent "
                "rounds. Current allotment permanently confirmed."
            ),
            "use_when":   "You are fully happy with your current seat.",
            "risk":       "NONE — your seat is confirmed.",
            "safe":       True
        },
        "FLOAT": {
            "title":      "FLOAT — Try for Better NIT or Branch",
            "definition": (
                "Considered for ALL better-preferred choices across "
                "ANY institute in the next round. If better allotted, "
                "current seat is forfeited. If nothing better is "
                "allotted, you RETAIN your current seat."
            ),
            "use_when":   (
                "You want to try for a better NIT or branch anywhere. "
                "Completely safe — cannot get worse."
            ),
            "risk":       "NONE — you keep current seat if nothing better.",
            "safe":       True
        },
        "SLIDE": {
            "title":      "SLIDE — Try for Better Branch at Same NIT",
            "definition": (
                "Considered for better-preferred choices ONLY within "
                "the SAME institute. If nothing better within same NIT "
                "you RETAIN your current seat."
            ),
            "use_when":   (
                "You want a better branch at the same NIT. "
                "Completely safe — cannot get worse."
            ),
            "risk":       "NONE — you keep current branch if nothing better.",
            "safe":       True
        }
    }