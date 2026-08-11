from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.auth import decode_token

router = APIRouter()

# ---------- Helper: Generate ordered list ----------

def generate_preference_list(safe, target, ambitious, student):

    preferences = []
    counter = 1
    home_nit = student.get("home_state_nit", "")

    # Step 1: Add ambitious first (nothing to lose)
    for nit in ambitious:
        for program in nit.get("mtech_programs", [{"short_name": "CSE"}]):
            preferences.append({
                "preference_no": counter,
                "nit_code": nit.get("nit_code"),
                "nit_name": nit.get("nit_name"),
                "branch": program.get("short_name", "CSE"),
                "category": student.get("category", "UR"),
                "bucket": "Ambitious",
                "probability": nit.get("admission_probability"),
                "note": "Dream choice — worth trying"
            })
            counter += 1

    # Step 2: Add target choices
    for nit in target:
        for program in nit.get("mtech_programs", [{"short_name": "CSE"}]):
            preferences.append({
                "preference_no": counter,
                "nit_code": nit.get("nit_code"),
                "nit_name": nit.get("nit_name"),
                "branch": program.get("short_name", "CSE"),
                "category": student.get("category", "UR"),
                "bucket": "Target",
                "probability": nit.get("admission_probability"),
                "note": "Realistic target — good chances"
            })
            counter += 1

    # Step 3: Add safe choices last
    for nit in safe:
        note = "Safety net — very likely"
        if nit.get("home_state"):
            note = "Home state safety net — almost certain"
        for program in nit.get("mtech_programs", [{"short_name": "CSE"}]):
            preferences.append({
                "preference_no": counter,
                "nit_code": nit.get("nit_code"),
                "nit_name": nit.get("nit_name"),
                "branch": program.get("short_name", "CSE"),
                "category": student.get("category", "UR"),
                "bucket": "Safe",
                "probability": nit.get("admission_probability"),
                "note": note
            })
            counter += 1

    return preferences


# ---------- Part 1 Choice Filing ----------

@router.get("/choice-filing/part1")
async def get_part1_list(token: str):
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

    # Get recommendations
    from app.routes.recommend import score_nit
    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)
    scored = [score_nit(nit, student) for nit in nits]
    scored.sort(key=lambda x: x["total_score"], reverse=True)

    safe = [n for n in scored if n["bucket"] == "Safe"]
    target = [n for n in scored if n["bucket"] == "Target"]
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]

    # Generate preference list
    preferences = generate_preference_list(
        safe, target, ambitious, student
    )

    return {
        "part": "Part 1 — Regular Rounds (R1, R2, R3)",
        "instruction": "Submit this list ONCE before Round 1 starts. Same list is used for all 3 regular rounds.",
        "student": {
            "name": student.get("full_name"),
            "gate_score": student.get("gate_score"),
            "category": student.get("category")
        },
        "total_preferences": len(preferences),
        "preferences": preferences,
        "why_this_order": "Ambitious choices are placed first because CCMT gives your highest eligible preference automatically. Safe choices at the bottom ensure you never go empty handed.",
        "important_note": f"Your home state NIT ({student.get('home_state_nit', 'N/A')}) is your safety net. Never leave counselling without it in your list."
    }


# ---------- Part 2 Choice Filing ----------

@router.post("/choice-filing/part2")
async def get_part2_list(token: str, current_allocation: str):
    db = get_db()

    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email},
        {"_id": 0, "password": 0}
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get recommendations
    from app.routes.recommend import score_nit
    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)
    scored = [score_nit(nit, student) for nit in nits]
    scored.sort(key=lambda x: x["total_score"], reverse=True)

    # Remove current allocation from ambitious
    # Focus on upgrades only
    safe = [n for n in scored if n["bucket"] == "Safe"]
    target = [n for n in scored if n["bucket"] == "Target"]
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]

    preferences = generate_preference_list(
        safe, target, ambitious, student
    )

    return {
        "part": "Part 2 — Special Rounds (SR1, SR2)",
        "instruction": "Submit this NEW list before Special Round 1. This is different from Part 1.",
        "current_allocation": current_allocation,
        "student": {
            "name": student.get("full_name"),
            "gate_score": student.get("gate_score"),
            "category": student.get("category")
        },
        "total_preferences": len(preferences),
        "preferences": preferences,
        "important_note": f"You currently have {current_allocation}. This list focuses on upgrading your seat in Special Rounds."
    }


# ---------- Lock Float Slide Advisor ----------

@router.post("/advisor")
async def lock_float_slide(
    token: str,
    current_allocation: str,
    target_nit: str
):
    db = get_db()

    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email},
        {"_id": 0, "password": 0}
    )

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    gate_score = student.get("gate_score", 0)
    category = student.get("category", "UR")

    # Find target NIT probability
    from app.routes.recommend import score_nit
    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)

    target_data = None
    for nit in nits:
        if nit.get("name") == target_nit or nit.get("nit_code") == target_nit:
            target_data = score_nit(nit, student)
            break

    if not target_data:
        return {
            "recommendation": "LOCK",
            "reason": f"Target NIT {target_nit} not found. Keep your current allocation safely."
        }

    probability = target_data.get("admission_probability", 0)

    # Decision logic
    if probability >= 70:
        recommendation = "FLOAT"
        reason = f"High chance ({probability}%) of getting {target_nit}. Float safely — you keep {current_allocation} as backup."
        risk = "LOW"
    elif probability >= 40:
        recommendation = "FLOAT"
        reason = f"Moderate chance ({probability}%) of getting {target_nit}. Floating is worth it — {current_allocation} stays safe."
        risk = "MEDIUM"
    elif probability >= 20:
        recommendation = "LOCK"
        reason = f"Low chance ({probability}%) of getting {target_nit}. Better to lock {current_allocation} and secure it."
        risk = "HIGH"
    else:
        recommendation = "LOCK"
        reason = f"Very low chance ({probability}%) of getting {target_nit}. Lock {current_allocation} immediately."
        risk = "VERY HIGH"

    return {
        "current_allocation": current_allocation,
        "target_nit": target_nit,
        "target_probability": probability,
        "recommendation": recommendation,
        "risk_level": risk,
        "reason": reason,
        "options": {
            "LOCK": {
                "description": f"Accept {current_allocation} and exit counselling",
                "pro": "100% secure seat",
                "con": f"Lose chance at {target_nit}"
            },
            "FLOAT": {
                "description": f"Keep {current_allocation} and stay in counselling",
                "pro": f"Still have {current_allocation} as safety + chance at upgrade",
                "con": "Small fee to pay for seat acceptance"
            },
            "SLIDE": {
                "description": f"Release {current_allocation} to try for better",
                "pro": "Higher preferences still possible",
                "con": f"Risk losing {current_allocation} permanently"
            }
        }
    }