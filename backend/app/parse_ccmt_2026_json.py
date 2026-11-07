"""
ASCENT Phase 3A — Parse CCMT 2026 JSON and Store in MongoDB

Parses ccmt_2026_final.json (downloaded via browser
console from the CCMT 2026 OR-CR DataTable) and stores
filtered CSE/DA records into the ccmt_cutoffs collection.

Input file location:
  backend/data/raw/ccmt_2026_final.json

Format: array of arrays
  [Sr.No, Round, Institute, PG Program,
   Group, Category, Max Score, Min Score]

After running this script, ccmt_cutoffs will contain
2021-2026 data (6 years) ready for Phase 3B backtest.
"""

import asyncio
import json
import html
import sys
import os

sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from motor.motor_asyncio import AsyncIOMotorClient
from app.process_cutoffs import (
    normalise_institute_code,
    classify_programme,
)

MONGODB_URL   = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

JSON_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "raw", "parsed", "ccmt_2026_final.json"
)

# Round name normalisation
ROUND_MAP = {
    "round 1":             "Round 1",
    "round 2":             "Round 2",
    "round 3":             "Round 3",
    "round-1":             "Round 1",
    "round-2":             "Round 2",
    "round-3":             "Round 3",
    "round-i":             "Round 1",
    "round-ii":            "Round 2",
    "round-iii":           "Round 3",
    "special round-i":     "Special Round 1",
    "special round-ii":    "Special Round 2",
    "special round 1":     "Special Round 1",
    "special round 2":     "Special Round 2",
    "national spot round": "National Spot Round",
}

# Category normalisation
CATEGORY_MAP = {
    "open":     "UR",
    "obc-ncl":  "OBC",
    "sc":       "SC",
    "st":       "ST",
    "ews":      "EWS",
    "open-pwd": "UR",
    "obc-pwd":  "OBC",
    "sc-pwd":   "SC",
    "st-pwd":   "ST",
    "ews-pwd":  "EWS",
}


def parse_json_file(filepath: str) -> list:
    """
    Read and parse the 2026 JSON file.
    Format: array of arrays.
    Returns list of raw dicts.
    """
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        print(f"\nExpected location:")
        print(f"  backend/data/raw/ccmt_2026_final.json")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Total rows in JSON: {len(data)}")

    if not data:
        print("❌ Empty JSON")
        return []

    first = data[0]

    # Confirm it is array of arrays format
    if not isinstance(first, list):
        print(f"❌ Unexpected format: {type(first)}")
        print(f"   First element: {first}")
        return []

    print(f"Format confirmed: array of arrays")
    print(f"Columns per row: {len(first)}")
    print(f"Sample row 0: {first}")

    rows = []
    for row in data:
        if len(row) < 7:
            continue

        # Decode HTML entities (&amp; → &, etc.)
        institute = html.unescape(str(row[2]).strip())
        programme = html.unescape(str(row[3]).strip())
        round_raw = html.unescape(str(row[1]).strip())
        cat_raw   = html.unescape(str(row[5]).strip())
        max_s     = str(row[6]).strip()
        min_s     = str(row[7]).strip() if len(row) > 7 \
                    else str(row[6]).strip()

        rows.append({
            "round_raw":    round_raw,
            "institute":    institute,
            "programme":    programme,
            "category_raw": cat_raw,
            "max_score_s":  max_s,
            "min_score_s":  min_s,
        })

    print(f"Loaded {len(rows)} rows after basic parse")
    return rows


def filter_and_normalise(raw_rows: list) -> list:
    """
    Filter to our 31 target NITs and CSE/DA branches.
    Normalise round names and categories.
    """
    clean     = []
    skipped   = 0
    no_nit    = set()
    no_branch = set()

    for r in raw_rows:
        # Parse numeric scores
        try:
            max_score = float(r["max_score_s"]) \
                        if r["max_score_s"] else None
            min_score = float(r["min_score_s"]) \
                        if r["min_score_s"] else None
        except ValueError:
            skipped += 1
            continue

        if not min_score or min_score <= 0:
            skipped += 1
            continue

        # Match to our NIT code
        nit_code = normalise_institute_code(r["institute"])
        if nit_code == "UNKNOWN":
            no_nit.add(r["institute"])
            skipped += 1
            continue

        # Match to our branch code
        branch_code = classify_programme(r["programme"])
        if branch_code is None:
            no_branch.add(r["programme"])
            skipped += 1
            continue

        # Normalise category
        category = CATEGORY_MAP.get(
            r["category_raw"].strip().lower()
        )
        if category is None:
            skipped += 1
            continue

        # Normalise round name
        round_key  = r["round_raw"].strip().lower()
        round_name = ROUND_MAP.get(round_key, r["round_raw"])

        clean.append({
            "year":           2026,
            "round":          round_name,
            "institute_code": nit_code,
            "institute_name": r["institute"],
            "programme_name": r["programme"],
            "branch_code":    branch_code,
            "category":       category,
            "max_score":      max_score,
            "min_score":      min_score,
        })

    print(f"\nFiltering results:")
    print(f"  Valid CSE/DA NIT records : {len(clean)}")
    print(f"  Skipped                  : {skipped}")

    if no_nit:
        print(f"\n  Unmatched institutes ({len(no_nit)} unique):")
        for n in sorted(no_nit)[:8]:
            print(f"    {n[:60]}")

    if no_branch:
        print(f"\n  Non-CSE/DA programmes ({len(no_branch)} unique):")
        for b in sorted(no_branch)[:8]:
            print(f"    {b[:60]}")

    return clean


def show_summary(records: list):
    """Print per-NIT and per-round breakdown."""
    if not records:
        return

    print(f"\n{'='*55}")
    print("Per-NIT branch coverage:")
    print(f"{'='*55}")

    by_nit = {}
    for r in records:
        nit = r["institute_code"]
        br  = r["branch_code"]
        by_nit.setdefault(nit, {})
        by_nit[nit][br] = by_nit[nit].get(br, 0) + 1

    for nit, branches in sorted(by_nit.items()):
        summary = [f"{b}({c})" for b, c in branches.items()]
        print(f"  {nit:8s}: {summary}")

    print(f"\nPer-round record count:")
    round_counts = {}
    for r in records:
        rnd = r["round"]
        round_counts[rnd] = round_counts.get(rnd, 0) + 1
    for rnd, count in sorted(round_counts.items()):
        print(f"  {rnd:25s}: {count}")


async def save_to_mongodb(records: list):
    """
    Delete existing 2026 records and insert fresh ones.
    Re-run safe.
    """
    client = AsyncIOMotorClient(MONGODB_URL)
    db     = client[DATABASE_NAME]

    # Delete any existing 2026 records
    deleted = await db["ccmt_cutoffs"].delete_many(
        {"year": 2026}
    )
    if deleted.deleted_count > 0:
        print(f"\nRemoved {deleted.deleted_count} "
              f"existing 2026 records (re-run)")

    # Insert new records
    if records:
        await db["ccmt_cutoffs"].insert_many(records)
        print(f"Inserted {len(records)} 2026 records")

    # Print year-wise totals
    print(f"\nccmt_cutoffs — year-wise record counts:")
    grand_total = 0
    for y in [2021, 2022, 2023, 2024, 2025, 2026]:
        count = await db["ccmt_cutoffs"].count_documents(
            {"year": y}
        )
        grand_total += count
        tag = "  ← TEST SET (held-out)" if y == 2026 else ""
        tag = "  ← TRAINING DATA"       if y < 2026  else tag
        print(f"  {y}: {count:>5,} records{tag}")
    print(f"  {'TOTAL':4s}: {grand_total:>5,} records")

    # Quick sanity check — show 3 real 2026 CSE records
    sample = await db["ccmt_cutoffs"].find(
        {"year": 2026, "branch_code": "CSE",
         "round": "Round 1", "category": "UR"},
        {"_id": 0, "institute_code": 1,
         "min_score": 1, "max_score": 1}
    ).limit(5).to_list(5)

    if sample:
        print(f"\nSanity check — 2026 R1 UR CSE closing scores:")
        for s in sample:
            print(f"  {s['institute_code']:8s} | "
                  f"closing={s['min_score']} | "
                  f"opening={s['max_score']}")

    client.close()


async def run():
    print("=" * 60)
    print("ASCENT Phase 3A — Parse CCMT 2026 JSON")
    print("=" * 60)
    print(f"Input: {JSON_FILE}")
    print()

    # Step 1: Parse JSON
    raw_rows = parse_json_file(JSON_FILE)
    if not raw_rows:
        return

    # Step 2: Show first 3 rows for verification
    print(f"\nFirst 3 raw rows (verify format):")
    for r in raw_rows[:3]:
        print(f"  institute : {r['institute'][:50]}")
        print(f"  programme : {r['programme'][:50]}")
        print(f"  round     : {r['round_raw']}")
        print(f"  category  : {r['category_raw']}")
        print(f"  min_score : {r['min_score_s']}")
        print()

    # Step 3: Filter and normalise
    clean = filter_and_normalise(raw_rows)
    if not clean:
        print("\n❌ No valid records after filtering.")
        print("Check the raw rows printed above.")
        return

    # Step 4: Show summary
    show_summary(clean)

    # Step 5: Save to MongoDB
    print(f"\nSaving {len(clean)} records to MongoDB...")
    await save_to_mongodb(clean)

    print(f"\n{'='*60}")
    print("Phase 3A COMPLETE")
    print("Next step: python app/phase3_backtest.py")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(run())