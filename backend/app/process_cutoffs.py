"""
ASCENT — Process Raw CCMT Cutoff Data
Reads raw scraped JSON (all years, all programmes, all
target NITs), filters down to CSE/DA relevant programmes
only, normalizes institute codes / branch codes / category
names, and stores the clean combined dataset in MongoDB.
"""

import json
import os
import re
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

RAW_DIR = "../data/raw/parsed"
MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

YEARS = [2021, 2022, 2023, 2024, 2025]


# ── Programme filtering: keyword → branch code ─────────────
# Order matters: more specific keywords checked first so a
# programme only gets ONE branch code assigned.

BRANCH_KEYWORD_MAP = [
    ("CY",  ["cyber security", "cyber forensics"]),
    ("IS",  ["information security", "information systems security"]),
    ("AI",  ["artificial intelligence", "robotics & artificial intelligence"]),
    ("DS",  ["data science", "computational and data science", "data analytics"]),
    ("DE",  ["data engineering"]),
    ("SE",  ["software engineering", "agile software engineering"]),
    ("IT",  ["information technology", "communication & information technology"]),
    ("CSE", ["computer science", "computer engineering"]),
    ("MC",  ["mathematics and computing", "mathematics & computing"]),
]

# Dual-degree IT programmes: department is IT but title
# doesn't literally say "Information Technology"
DUAL_DEGREE_IT_PATTERNS = [
    r"dual degree.*ph\.?d.*\bit\b.*specialization",
    r"m\.?tech\.?\s*it\s*with specialization",
]

# Programmes that ALSO contain "data analytics" as a
# secondary signal (catches things like "Industrial
# Engineering and Data Analytics" only if we want them —
# currently NOT included, kept strict to core CSE/DA)


def classify_programme(programme_name: str):
    """
    Returns a short branch code (CSE, AI, DS, DE, IT, CY,
    SE, IS, MC) if the programme is CSE/DA relevant,
    otherwise returns None.
    """
    name_lower = programme_name.lower()

    # Check dual-degree IT special cases first
    for pattern in DUAL_DEGREE_IT_PATTERNS:
        if re.search(pattern, name_lower):
            return "IT"

    # Check standard keyword map, in priority order
    for code, keywords in BRANCH_KEYWORD_MAP:
        for kw in keywords:
            if kw in name_lower:
                return code

    return None


# ── Institute name → code normalization ─────────────────────

INSTITUTE_CODE_MAP = {
    "agartala":            "NITA",
    "andhra pradesh":      "NITAP",
    "arunachal pradesh":   "NITAR",
    "calicut":             "NITC",
    "delhi":               "NITD",
    "durgapur":            "NITDGP",
    "goa":                 "NITGOA",
    "hamirpur":            "NITH",
    "jalandhar":           "NITJ",
    "jamshedpur":          "NITJSR",
    "jaipur":              "MNIT",
    "karnataka, surathkal":"NITK",
    "kurukshetra":         "NITKKR",
    "manipur":             "NITMN",
    "meghalaya":           "NITM",
    "mizoram":             "NITMZ",
    "nagaland":            "NITNGL",
    "nagpur":              "VNIT",
    "patna":               "NITP",
    "puducherry":          "NITPY",
    "raipur":              "NITRR",
    "rourkela":            "NITRK",
    "silchar":             "NITSLR",
    "sikkim":              "NITSKM",
    "srinagar":            "NITSR",
    "surat":               "SVNIT",
    "tiruchirappalli":     "NITT",
    "uttarakhand":         "NITUK",
    "warangal":            "NITW",
    "allahabad":           "MNNIT",
    "bhopal":              "MANIT",
}


def normalise_institute_code(institute_name: str) -> str:
    """
    Maps a full institute name to our NIT code.
    Strictly requires 'National Institute of Technology'
    to appear in the name (this correctly matches all real
    NITs including specially-named ones like Sardar
    Vallabhbhai NIT, Visvesvaraya NIT, Malaviya NIT, etc.)
    and explicitly rejects IIITs, IITs, and other institutes
    that happen to share a city name with an NIT.
    """
    name_lower = institute_name.lower()

    # Explicitly reject non-NIT institutes first —
    # prevents city-name collisions (e.g. IIIT Bhopal
    # vs NIT Bhopal / MANIT)
    exclusion_keywords = [
        "indian institute of information technology",
        "iiit",
        "indian institute of technology",
        " iit ",
        "central university",
        "central institute of technology",
    ]
    for excl in exclusion_keywords:
        if excl in name_lower:
            return "UNKNOWN"

    # Must explicitly be a National Institute of Technology
    # (covers standard NITs and specially-named ones like
    # "Sardar Vallabhbhai National Institute of Technology")
    if "national institute of technology" not in name_lower:
        return "UNKNOWN"

    for key, code in INSTITUTE_CODE_MAP.items():
        if key in name_lower:
            return code

    return "UNKNOWN"


# ── Category normalization ───────────────────────────────────

CATEGORY_MAP = {
    "OPEN":         "UR",
    "GEN":          "UR",
    "GENERAL":      "UR",
    "UR":           "UR",
    "OBC-NCL":      "OBC",
    "OBC":          "OBC",
    "SC":           "SC",
    "ST":           "ST",
    "EWS":          "EWS",
}


def normalise_category(cat: str) -> str:
    cat = cat.upper().strip()
    return CATEGORY_MAP.get(cat, cat)


# ── Score parsing ─────────────────────────────────────────────

def parse_score(text: str):
    text = (text or "").strip()
    if not text or text in ["-", "--", "N/A", "NA"]:
        return None
    match = re.search(r"[\d.]+", text)
    return float(match.group()) if match else None


# ── Load, filter, normalize all years ────────────────────────

def process_all_years():
    all_clean_records = []
    stats = {"total_raw": 0, "kept_cse_da": 0}

    for year in YEARS:
        filepath = os.path.join(RAW_DIR, f"ccmt_{year}_final.json")
        if not os.path.exists(filepath):
            print(f"⚠️ Missing file for {year}, skipping")
            continue

        with open(filepath, "r", encoding="utf-8") as f:
            raw_records = json.load(f)

        stats["total_raw"] += len(raw_records)
        year_kept = 0

        for r in raw_records:
            programme = r.get("pg program", "")
            branch_code = classify_programme(programme)

            if branch_code is None:
                continue  # not CSE/DA relevant, skip

            institute_code = normalise_institute_code(r.get("institute", ""))
            if institute_code == "UNKNOWN":
                continue  # not one of our 31 target NITs

            min_score = parse_score(r.get("min gate score", ""))
            max_score = parse_score(r.get("max gate score", ""))

            if min_score is None:
                continue  # no usable score data

            clean_record = {
                "year": r.get("year", year),
                "round": r.get("round", "").strip(),
                "institute_code": institute_code,
                "institute_name": r.get("institute", "").strip(),
                "programme_name": programme.strip(),
                "branch_code": branch_code,
                "group": r.get("group", "").strip(),
                "category": normalise_category(r.get("category", "")),
                "max_score": max_score,
                "min_score": min_score,
            }

            all_clean_records.append(clean_record)
            year_kept += 1

        stats["kept_cse_da"] += year_kept
        print(f"{year}: {len(raw_records)} raw → {year_kept} CSE/DA relevant kept")

    print(f"\n{'='*60}")
    print(f"Total raw records processed: {stats['total_raw']}")
    print(f"Total CSE/DA relevant kept:  {stats['kept_cse_da']}")
    print(f"{'='*60}")

    return all_clean_records


# ── Save to MongoDB ─────────────────────────────────────────

async def save_to_mongodb(records: list):
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    await db["ccmt_cutoffs"].delete_many({})
    if records:
        result = await db["ccmt_cutoffs"].insert_many(records)
        print(f"\n✅ Saved {len(result.inserted_ids)} records to "
              f"MongoDB collection: ccmt_cutoffs")

    # Quick summary by institute
    institutes = sorted(set(r["institute_code"] for r in records))
    print(f"\nInstitutes represented: {len(institutes)}")
    for inst in institutes:
        count = sum(1 for r in records if r["institute_code"] == inst)
        print(f"  {inst}: {count} records")

    # Quick summary by branch
    branches = sorted(set(r["branch_code"] for r in records))
    print(f"\nBranches represented: {branches}")
    for br in branches:
        count = sum(1 for r in records if r["branch_code"] == br)
        print(f"  {br}: {count} records")

    client.close()


# ── Also save a clean local JSON copy for reference ─────────

def save_clean_json(records: list):
    os.makedirs("../data/processed", exist_ok=True)
    filepath = "../data/processed/ccmt_cutoffs_clean.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"\nAlso saved clean copy to: {filepath}")


if __name__ == "__main__":
    records = process_all_years()
    save_clean_json(records)
    asyncio.run(save_to_mongodb(records))