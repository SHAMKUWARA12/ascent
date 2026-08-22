from fastapi import APIRouter, HTTPException
from app.database import get_db
from app.auth import decode_token

router = APIRouter()

# ─────────────────────────────────────────────────────────
# OFFICIAL CCMT DEFINITIONS:
#
# LOCK: Accept current seat. Exit counselling. Final.
#
# FLOAT:  Be considered for ALL better-preferred choices
#         across ANY institute in next round.
#         SAFE — retain current if nothing better allotted.
#
# SLIDE:  Be considered for better-preferred choices ONLY
#         within the SAME institute.
#         SAFE — retain current if nothing better at same NIT.
# ─────────────────────────────────────────────────────────


# ── Generate preference list ──────────────────────────────

def generate_preference_list(safe, target, ambitious, student):
    preferences = []
    counter = 1
    branch_priorities = student.get("branch_priorities", [])

    def get_branch_priority(branch):
        try:
            return branch_priorities.index(branch.upper())
        except ValueError:
            return 999

    def sort_by_branch(items):
        return sorted(
            items,
            key=lambda x: get_branch_priority(x.get("branch", ""))
        )

    for nit in sort_by_branch(ambitious):
        preferences.append({
            "preference_no": counter,
            "nit_code": nit.get("nit_code"),
            "nit_name": nit.get("nit_name"),
            "branch": nit.get("branch"),
            "branch_full": nit.get("branch_full"),
            "category": student.get("category", "UR"),
            "bucket": "Ambitious",
            "probability": nit.get("admission_probability"),
            "note": "Dream choice — worth including"
        })
        counter += 1

    for nit in sort_by_branch(target):
        preferences.append({
            "preference_no": counter,
            "nit_code": nit.get("nit_code"),
            "nit_name": nit.get("nit_name"),
            "branch": nit.get("branch"),
            "branch_full": nit.get("branch_full"),
            "category": student.get("category", "UR"),
            "bucket": "Target",
            "probability": nit.get("admission_probability"),
            "note": "Realistic target — good chances"
        })
        counter += 1

    for nit in sort_by_branch(safe):
        note = "Safety net — very likely"
        if nit.get("home_state"):
            note = "Home state safety net — almost certain"
        preferences.append({
            "preference_no": counter,
            "nit_code": nit.get("nit_code"),
            "nit_name": nit.get("nit_name"),
            "branch": nit.get("branch"),
            "branch_full": nit.get("branch_full"),
            "category": student.get("category", "UR"),
            "bucket": "Safe",
            "probability": nit.get("admission_probability"),
            "note": note
        })
        counter += 1

    return preferences


# ── Get all scored NITs ───────────────────────────────────

async def get_scored_nits(student, db):
    from app.routes.recommend import score_nit_programme
    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)
    scored = []
    for nit in nits:
        for programme in nit.get("mtech_programs", []):
            result = score_nit_programme(nit, programme, student)
            if result:
                scored.append(result)
    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored


# ── Find preference number for a given NIT + branch ───────

def find_preference_no(preferences, nit_name, branch):
    for p in preferences:
        if (p["nit_name"].lower() == nit_name.lower() and
                p["branch"].upper() == branch.upper()):
            return p["preference_no"]
    return None


# ── Standard options explanation (always shown) ───────────

def build_options(current_nit, current_branch, target_nit, target_branch):
    current = f"{current_nit} — {current_branch}"
    target  = f"{target_nit} — {target_branch}"
    return {
        "LOCK": {
            "what_it_means": (
                "You are satisfied with your current seat. "
                "You will NOT be considered for any better choices "
                "in subsequent rounds. Your current allotment is confirmed."
            ),
            "pro": (
                f"Your seat at {current} is 100% confirmed. "
                "No uncertainty whatsoever."
            ),
            "con": (
                "You permanently exit counselling. "
                "Cannot participate in future rounds or upgrades."
            )
        },
        "FLOAT": {
            "what_it_means": (
                "You are considered for ALL better-preferred choices "
                "across ALL institutes in the next round. "
                "If a better choice is allotted, your current allotment "
                "is forfeited. If nothing better is allotted, "
                "you retain your current allotment. SAFE option."
            ),
            "pro": (
                f"Safe — you retain {current} if nothing better opens up. "
                "Considers your entire preference list above current seat."
            ),
            "con": (
                f"If a better choice IS allotted, "
                f"{current} is automatically forfeited. "
                "Only float if you are willing to accept the upgrade."
            )
        },
        "SLIDE": {
            "what_it_means": (
                f"You are considered for better-preferred choices "
                f"ONLY within {current_nit}. "
                "If nothing better within that institute is allotted, "
                "you retain your current allotment. SAFE option."
            ),
            "pro": (
                f"Safe — you retain {current} if no better branch "
                f"opens at {current_nit}. "
                f"Useful when you want to upgrade branch within same NIT."
            ),
            "con": (
                f"Limited to {current_nit} only. "
                "You miss chances at better branches in other institutes."
            )
        }
    }


# ── Part 1 Choice Filing ──────────────────────────────────

@router.get("/choice-filing/part1")
async def get_part1_list(token: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email}, {"_id": 0, "password": 0}
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if not student.get("profile_complete"):
        raise HTTPException(
            status_code=400,
            detail="Please complete your profile first"
        )

    scored = await get_scored_nits(student, db)
    safe      = [n for n in scored if n["bucket"] == "Safe"]
    target    = [n for n in scored if n["bucket"] == "Target"]
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]
    preferences = generate_preference_list(safe, target, ambitious, student)

    return {
        "part": "Part 1 — Regular Rounds (R1, R2, R3)",
        "instruction": (
            "Submit this list ONCE before Round 1 starts. "
            "The same list is used for all 3 regular rounds."
        ),
        "student": {
            "name": student.get("full_name"),
            "gate_score": student.get("gate_score"),
            "category": student.get("category")
        },
        "total_preferences": len(preferences),
        "preferences": preferences,
        "why_this_order": (
            "Ambitious choices are placed first because CCMT gives "
            "your highest eligible preference automatically. "
            "Safe choices at the bottom ensure you never go empty handed."
        ),
        "important_note": (
            f"Your home state NIT "
            f"({student.get('home_state_nit', 'N/A')}) "
            f"is your safety net. Always keep it in your list."
        )
    }


# ── Part 2 Choice Filing ──────────────────────────────────

@router.post("/choice-filing/part2")
async def get_part2_list(token: str, current_allocation: str):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email}, {"_id": 0, "password": 0}
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    scored = await get_scored_nits(student, db)
    safe      = [n for n in scored if n["bucket"] == "Safe"]
    target    = [n for n in scored if n["bucket"] == "Target"]
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]
    preferences = generate_preference_list(safe, target, ambitious, student)

    return {
        "part": "Part 2 — Special Rounds (SR1, SR2)",
        "instruction": (
            "Submit this NEW list before Special Round 1. "
            "This is different from your Part 1 list."
        ),
        "current_allocation": current_allocation,
        "student": {
            "name": student.get("full_name"),
            "gate_score": student.get("gate_score"),
            "category": student.get("category")
        },
        "total_preferences": len(preferences),
        "preferences": preferences,
        "important_note": (
            f"You currently have {current_allocation}. "
            "This list helps you upgrade during Special Rounds."
        )
    }


# ── Advisor ───────────────────────────────────────────────

@router.post("/advisor")
async def advisor(
    token: str,
    current_nit: str,
    current_branch: str,
    target_nit: str,
    target_branch: str
):
    db = get_db()
    payload = decode_token(token)
    email = payload.get("sub")

    student = await db["students"].find_one(
        {"email": email}, {"_id": 0, "password": 0}
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    options = build_options(
        current_nit, current_branch,
        target_nit, target_branch
    )

    # ── Validate: same seat ───────────────────────────────
    if (current_nit.strip().lower() == target_nit.strip().lower() and
            current_branch.strip().upper() == target_branch.strip().upper()):
        return {
            "recommendation": "LOCK",
            "risk_level": "NONE",
            "reason": (
                f"Your current seat ({current_nit} — {current_branch}) "
                f"and target are identical. "
                f"If you are satisfied with this seat, choose LOCK "
                f"to confirm it and exit counselling."
            ),
            "current_nit": current_nit,
            "current_branch": current_branch,
            "target_nit": target_nit,
            "target_branch": target_branch,
            "target_probability": 100,
            "same_nit": True,
            "preference_context": None,
            "options": options
        }

    # ── Get ASCENT preference list ────────────────────────
    scored = await get_scored_nits(student, db)
    safe      = [n for n in scored if n["bucket"] == "Safe"]
    target_b  = [n for n in scored if n["bucket"] == "Target"]
    ambitious = [n for n in scored if n["bucket"] == "Ambitious"]
    preferences = generate_preference_list(
        safe, target_b, ambitious, student
    )

    current_pref_no = find_preference_no(
        preferences, current_nit, current_branch
    )
    target_pref_no = find_preference_no(
        preferences, target_nit, target_branch
    )

    # ── Get target probability ────────────────────────────
    from app.routes.recommend import score_nit_programme
    nits = await db["nits"].find({}, {"_id": 0}).to_list(length=100)

    probability  = 0
    current_nirf = 999
    target_nirf  = 999

    for nit in nits:
        name_lower = nit.get("name", "").lower()
        code_lower = nit.get("nit_code", "").lower()

        if (name_lower == current_nit.strip().lower() or
                code_lower == current_nit.strip().lower()):
            current_nirf = nit.get("nirf_rank", 999)

        if (name_lower == target_nit.strip().lower() or
                code_lower == target_nit.strip().lower()):
            target_nirf = nit.get("nirf_rank", 999)
            for prog in nit.get("mtech_programs", []):
                if target_branch:
                    if (prog.get("short_name", "").upper()
                            != target_branch.strip().upper()):
                        continue
                result = score_nit_programme(nit, prog, student)
                if result:
                    p = result.get("admission_probability", 0)
                    if p > probability:
                        probability = p

    same_nit = (
        current_nit.strip().lower() == target_nit.strip().lower()
    )

    # ── Check preference list context ─────────────────────
    preference_context = None
    if current_pref_no and target_pref_no:
        if target_pref_no < current_pref_no:
            preference_context = (
                f"Target (Pref #{target_pref_no}) is ranked HIGHER "
                f"than current (Pref #{current_pref_no}) in your "
                f"ASCENT preference list. "
                f"This is a valid upgrade direction."
            )
        else:
            preference_context = (
                f"Warning: Target (Pref #{target_pref_no}) is ranked "
                f"LOWER than current (Pref #{current_pref_no}) in your "
                f"ASCENT preference list. "
                f"CCMT will never allot something ranked lower than "
                f"your current seat. Consider LOCK instead."
            )

    # ══════════════════════════════════════════════════════
    # SAME NIT → Recommend SLIDE or LOCK
    #
    # SLIDE: considered for better preferences at SAME NIT.
    # Safe — retain current if nothing better at same NIT.
    #
    # When to recommend SLIDE:
    # Target is a better preferred branch at same NIT
    # (target preference no < current preference no)
    #
    # When to recommend LOCK:
    # Target branch is lower/equal priority → no benefit
    # ══════════════════════════════════════════════════════
    if same_nit:

        branch_priorities = student.get("branch_priorities", [])

        def branch_idx(b):
            try:
                return branch_priorities.index(b.upper())
            except ValueError:
                return 999

        current_idx = branch_idx(current_branch)
        target_idx  = branch_idx(target_branch)

        # Target branch is lower or equal priority
        if target_idx >= current_idx:
            recommendation = "LOCK"
            risk = "NONE"
            reason = (
                f"Your current branch ({current_branch}) is already "
                f"at a higher or equal priority compared to your "
                f"target ({target_branch}) at {current_nit}. "
                f"Sliding to a lower priority branch makes no sense. "
                f"LOCK your current seat — you already have the better option."
            )
        else:
            # Target branch is higher priority → SLIDE is appropriate
            # SLIDE is safe — you retain current if nothing better at same NIT
            recommendation = "SLIDE"
            risk = "LOW"
            if probability >= 60:
                reason = (
                    f"Good chance ({probability}%) of upgrading from "
                    f"{current_branch} to {target_branch} at {current_nit}. "
                    f"SLIDE is safe — if {target_branch} is not allotted "
                    f"you automatically retain {current_branch} at "
                    f"{current_nit}. You cannot lose your current seat."
                )
            elif probability >= 30:
                reason = (
                    f"Moderate chance ({probability}%) of getting "
                    f"{target_branch} at {current_nit}. "
                    f"SLIDE is still safe — you retain {current_branch} "
                    f"at {current_nit} if nothing better opens up. "
                    f"Worth trying as cutoffs may drop in later rounds."
                )
            else:
                reason = (
                    f"Low chance ({probability}%) this round but "
                    f"SLIDE is always safe — you retain {current_branch} "
                    f"at {current_nit} if {target_branch} cutoff does "
                    f"not come down. Keep sliding and wait for later rounds."
                )

        return {
            "recommendation": recommendation,
            "risk_level": risk,
            "reason": reason,
            "current_nit": current_nit,
            "current_branch": current_branch,
            "target_nit": target_nit,
            "target_branch": target_branch,
            "target_probability": probability,
            "same_nit": True,
            "current_nirf": current_nirf,
            "target_nirf": target_nirf,
            "current_preference_no": current_pref_no,
            "target_preference_no": target_pref_no,
            "preference_context": preference_context,
            "options": options
        }

    # ══════════════════════════════════════════════════════
    # DIFFERENT NIT → Recommend FLOAT or LOCK
    #
    # FLOAT: considered for ALL better-preferred choices
    # across ANY institute. Safe — retain current if nothing
    # better is allotted anywhere.
    #
    # When to recommend FLOAT:
    # Target is a better NIT or better branch at different NIT
    # (target preference no < current preference no)
    #
    # When to recommend LOCK:
    # Target is worse NIT with worse/equal branch
    # → Current seat is already better
    # ══════════════════════════════════════════════════════

    # Target is worse NIT AND branch not significantly better
    if (target_nirf > current_nirf and
            target_pref_no and current_pref_no and
            target_pref_no > current_pref_no):
        recommendation = "LOCK"
        risk = "NONE"
        reason = (
            f"Your current seat ({current_nit} — {current_branch}, "
            f"NIRF #{current_nirf}) is better than your target "
            f"({target_nit} — {target_branch}, NIRF #{target_nirf}). "
            f"Your target is also ranked lower (Pref #{target_pref_no}) "
            f"than your current seat (Pref #{current_pref_no}) in your "
            f"preference list. CCMT will never allot something ranked "
            f"lower than your current seat. LOCK your current seat."
        )
    else:
        # Target is better → FLOAT is safe and recommended
        # FLOAT is safe — retain current if nothing better anywhere
        recommendation = "FLOAT"
        risk = "LOW"
        if probability >= 60:
            reason = (
                f"Good chance ({probability}%) of getting "
                f"{target_nit} — {target_branch} (NIRF #{target_nirf}). "
                f"FLOAT is safe — if allotted, your {current_nit} "
                f"{current_branch} seat is forfeited and you get the "
                f"better option. If nothing better opens up you retain "
                f"{current_nit} — {current_branch}."
            )
        elif probability >= 30:
            reason = (
                f"Moderate chance ({probability}%) of getting "
                f"{target_nit} — {target_branch}. "
                f"FLOAT is safe — you retain {current_nit} "
                f"{current_branch} if nothing better is allotted. "
                f"Cutoffs typically drop in later rounds — keep floating."
            )
        else:
            reason = (
                f"Low chance ({probability}%) this round but "
                f"FLOAT is always safe for a better NIT. "
                f"You retain {current_nit} — {current_branch} if "
                f"{target_nit} {target_branch} cutoff does not come "
                f"down. Keep floating — no risk to your current seat."
            )

    return {
        "recommendation": recommendation,
        "risk_level": risk,
        "reason": reason,
        "current_nit": current_nit,
        "current_branch": current_branch,
        "target_nit": target_nit,
        "target_branch": target_branch,
        "target_probability": probability,
        "same_nit": False,
        "current_nirf": current_nirf,
        "target_nirf": target_nirf,
        "current_preference_no": current_pref_no,
        "target_preference_no": target_pref_no,
        "preference_context": preference_context,
        "options": options
    }