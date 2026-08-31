"""
ASCENT — Sentiment Pipeline Runner

Runs the full sentiment collection pipeline:
1. Computes GATE difficulty scores (2024-2026)
2. Computes NIT quality scores for all 31 NITs

Resume-safe: skips any GATE year or NIT that already has
real collected data (posts_analysed > 0), so re-running
this script only fills in gaps (e.g. NITs that hit YouTube's
daily quota limit on a previous run) rather than re-scraping
everything from scratch.

Usage:
    python run_sentiment.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.sentiment import calculate_gate_difficulty, calculate_nit_quality

MONGODB_URL   = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"
GATE_YEARS    = [2024, 2025, 2026]


async def get_all_nits_from_db():
    """Fetch the real 31 NITs from the nits collection."""
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    nits = await db["nits"].find(
        {}, {"_id": 0, "nit_code": 1, "name": 1}
    ).to_list(length=100)
    client.close()
    return [{"code": n["nit_code"], "name": n["name"]} for n in nits]


async def run():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    nits = await get_all_nits_from_db()
    print(f"Found {len(nits)} NITs to process for sentiment\n")

    # ── STEP 1: GATE difficulty scores ──────────────────────

    print("\n" + "="*50)
    print("STEP 1: Collecting GATE difficulty scores")
    print("="*50)

    existing_gate = await db["gate_difficulty"].count_documents({})
    if existing_gate == 0:
        for year in GATE_YEARS:
            print(f"\nAnalysing GATE {year}...")
            result = calculate_gate_difficulty(year)
            await db["gate_difficulty"].insert_one(result)
            print(f"  GATE {year}: {result['difficulty_score']}/10 — {result['label']}")
            print(f"  Posts analysed: {result['posts_analysed']}")
    else:
        print(f"GATE difficulty already has {existing_gate} records — skipping")

    # ── STEP 2: NIT quality scores ───────────────────────────

    print("\n" + "="*50)
    print("STEP 2: Collecting NIT quality scores (all 31 NITs)")
    print("="*50)

    already_done_docs = await db["nit_sentiment"].find(
        {}, {"nit_code": 1, "posts_analysed": 1}
    ).to_list(length=100)
    already_done = set(
        d["nit_code"] for d in already_done_docs
        if d.get("posts_analysed", 0) > 0
    )

    for nit in nits:
        if nit["code"] in already_done:
            print(f"\n⏭️  Skipping {nit['name']} — already has real sentiment data")
            continue

        print(f"\nAnalysing {nit['name']}...")
        result = calculate_nit_quality(nit["name"], nit["code"])

        await db["nit_sentiment"].delete_one({"nit_code": nit["code"]})
        await db["nit_sentiment"].insert_one(result)

        print(f"  Overall: {result['overall_score']}/10 — {result['label']}")
        print(f"  Placements: {result['placement_score']}/10")
        print(f"  Campus:     {result['campus_score']}/10")
        print(f"  Faculty:    {result['faculty_score']}/10")
        print(f"  Posts analysed: {result['posts_analysed']}")

    # ── Summary ────────────────────────────────────────────────

    gate_count = await db["gate_difficulty"].count_documents({})
    nit_count  = await db["nit_sentiment"].count_documents({})

    real_data_docs = await db["nit_sentiment"].find(
        {}, {"nit_code": 1, "posts_analysed": 1}
    ).to_list(length=100)
    real_count = sum(1 for d in real_data_docs if d.get("posts_analysed", 0) > 0)

    print("\n" + "="*50)
    print("SENTIMENT PIPELINE COMPLETE")
    print(f"GATE difficulty records: {gate_count}")
    print(f"NIT sentiment records:   {nit_count} / {len(nits)}")
    print(f"NITs with REAL data:     {real_count} / {len(nits)}")
    if real_count < len(nits):
        print(f"⚠️ {len(nits) - real_count} NITs still using fallback "
              f"defaults — likely YouTube quota. Re-run tomorrow to retry.")
    print("="*50)

    client.close()


if __name__ == "__main__":
    asyncio.run(run())