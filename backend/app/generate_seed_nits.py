"""
ASCENT — Generate seed_nits data from real scraped CCMT data.
Builds the nits collection using actual institute codes,
names, and programmes found in ccmt_cutoffs — guarantees
consistency between the nits collection and ccmt_cutoffs
collection (both derived from the same real scraped source).
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

# Full institute names, locations, and NIRF ranks
# (NIRF ranks are approximate/illustrative — to be
# replaced with real scraped NIRF data in a future step)
NIT_METADATA = {
    "NITA":   {"name": "NIT Agartala",         "location": "Agartala, Tripura",           "region": "East India",  "nirf_rank": 91},
    "NITAP":  {"name": "NIT Andhra Pradesh",   "location": "Tadepalligudem, AP",          "region": "South India", "nirf_rank": 82},
    "NITAR":  {"name": "NIT Arunachal Pradesh","location": "Yupia, Arunachal Pradesh",    "region": "East India",  "nirf_rank": 150},
    "NITC":   {"name": "NIT Calicut",          "location": "Calicut, Kerala",             "region": "South India", "nirf_rank": 12},
    "NITD":   {"name": "NIT Delhi",            "location": "Delhi",                       "region": "North India", "nirf_rank": 95},
    "NITDGP": {"name": "NIT Durgapur",         "location": "Durgapur, West Bengal",       "region": "East India",  "nirf_rank": 45},
    "NITGOA": {"name": "NIT Goa",              "location": "Farmagudi, Goa",              "region": "West India",  "nirf_rank": 100},
    "NITH":   {"name": "NIT Hamirpur",         "location": "Hamirpur, Himachal Pradesh",  "region": "North India", "nirf_rank": 65},
    "NITJ":   {"name": "NIT Jalandhar",        "location": "Jalandhar, Punjab",           "region": "North India", "nirf_rank": 55},
    "NITJSR": {"name": "NIT Jamshedpur",       "location": "Jamshedpur, Jharkhand",       "region": "East India",  "nirf_rank": 60},
    "MNIT":   {"name": "NIT Jaipur",           "location": "Jaipur, Rajasthan",           "region": "North India", "nirf_rank": 38},
    "NITK":   {"name": "NIT Surathkal",        "location": "Surathkal, Karnataka",        "region": "South India", "nirf_rank": 11},
    "NITKKR": {"name": "NIT Kurukshetra",      "location": "Kurukshetra, Haryana",        "region": "North India", "nirf_rank": 47},
    "NITMN":  {"name": "NIT Manipur",          "location": "Imphal, Manipur",             "region": "East India",  "nirf_rank": 130},
    "NITM":   {"name": "NIT Meghalaya",        "location": "Shillong, Meghalaya",         "region": "East India",  "nirf_rank": 145},
    "NITMZ":  {"name": "NIT Mizoram",          "location": "Aizawl, Mizoram",             "region": "East India",  "nirf_rank": 155},
    "NITNGL": {"name": "NIT Nagaland",         "location": "Dimapur, Nagaland",           "region": "East India",  "nirf_rank": 160},
    "VNIT":   {"name": "NIT Nagpur",           "location": "Nagpur, Maharashtra",         "region": "West India",  "nirf_rank": 33},
    "NITP":   {"name": "NIT Patna",            "location": "Patna, Bihar",                "region": "East India",  "nirf_rank": 70},
    "NITPY":  {"name": "NIT Puducherry",       "location": "Karaikal, Puducherry",        "region": "South India", "nirf_rank": 110},
    "NITRR":  {"name": "NIT Raipur",           "location": "Raipur, Chhattisgarh",        "region": "East India",  "nirf_rank": 75},
    "NITRK":  {"name": "NIT Rourkela",         "location": "Rourkela, Odisha",            "region": "East India",  "nirf_rank": 9},
    "NITSLR": {"name": "NIT Silchar",          "location": "Silchar, Assam",              "region": "East India",  "nirf_rank": 48},
    "NITSKM": {"name": "NIT Sikkim",           "location": "Ravangla, Sikkim",            "region": "East India",  "nirf_rank": 165},
    "NITSR":  {"name": "NIT Srinagar",         "location": "Srinagar, J&K",               "region": "North India", "nirf_rank": 90},
    "SVNIT":  {"name": "NIT Surat",            "location": "Surat, Gujarat",              "region": "West India",  "nirf_rank": 42},
    "NITT":   {"name": "NIT Trichy",           "location": "Tiruchirappalli, Tamil Nadu", "region": "South India", "nirf_rank": 8},
    "NITUK":  {"name": "NIT Uttarakhand",      "location": "Srinagar, Uttarakhand",       "region": "North India", "nirf_rank": 135},
    "NITW":   {"name": "NIT Warangal",         "location": "Warangal, Telangana",         "region": "South India", "nirf_rank": 5},
    "MNNIT":  {"name": "NIT Allahabad",        "location": "Prayagraj, Uttar Pradesh",    "region": "North India", "nirf_rank": 40},
    "MANIT":  {"name": "NIT Bhopal",           "location": "Bhopal, Madhya Pradesh",      "region": "West India",  "nirf_rank": 52},
}

# Final 8 branch codes confirmed via audit_branch_coverage.py
BRANCH_FULL_NAMES = {
    "CSE": "Computer Science & Engineering",
    "AI":  "Artificial Intelligence",
    "DS":  "Data Science & Engineering",
    "DE":  "Data Engineering",
    "IT":  "Information Technology",
    "CY":  "Cyber Security",
    "SE":  "Software Engineering",
    "IS":  "Information Security",
    "MC":  "Mathematics & Computing",
}


async def generate_nits():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    # Get all cutoff records that actually exist in our
    # verified, filtered real data
    cutoffs = await db["ccmt_cutoffs"].find({}, {"_id": 0}).to_list(length=10000)

    if not cutoffs:
        print("❌ ccmt_cutoffs collection is empty. "
              "Run process_cutoffs.py first.")
        client.close()
        return

    # Group programmes per institute per branch
    # (keep one representative programme name + track how
    # many years/rounds/categories we have data for, as a
    # quick data-richness signal)
    institute_programmes = {}
    for c in cutoffs:
        code = c["institute_code"]
        branch = c["branch_code"]
        prog_name = c["programme_name"]

        if code not in institute_programmes:
            institute_programmes[code] = {}

        if branch not in institute_programmes[code]:
            institute_programmes[code][branch] = {
                "name": prog_name,
                "record_count": 0
            }
        institute_programmes[code][branch]["record_count"] += 1

    # Build the nits documents
    nits_data = []
    skipped = []

    for code, meta in NIT_METADATA.items():
        programmes_at_this_nit = institute_programmes.get(code, {})

        if not programmes_at_this_nit:
            skipped.append(code)
            continue

        mtech_programs = []
        # Sort branches by record count (most data-rich first)
        # so the primary/most common programme appears first
        sorted_branches = sorted(
            programmes_at_this_nit.items(),
            key=lambda x: x[1]["record_count"],
            reverse=True
        )

        for branch_code, info in sorted_branches:
            mtech_programs.append({
                "program_id": f"{code}_{branch_code}",
                "official_name": info["name"],
                "short_name": branch_code,
                "short_name_full": BRANCH_FULL_NAMES.get(branch_code, branch_code),
                "gate_papers": ["CS", "DA"],  # both accepted; refine later if needed
                "has_hostel": True,
                # Exact seat counts and fees need separate scraping
                # from CCMT seat matrix — placeholder for now
                "seats": {"UR": None, "OBC": None, "SC": None, "ST": None, "EWS": None},
                "fee_annual": None,
                "historical_record_count": info["record_count"],
            })

        nits_data.append({
            "nit_code": code,
            "name": meta["name"],
            "location": meta["location"],
            "state": meta["location"].split(",")[-1].strip(),
            "region": meta["region"],
            "nirf_rank": meta["nirf_rank"],
            "mtech_programs": mtech_programs,
            "data_source": "CCMT OR-CR real scraped data (2021-2025)",
        })

    await db["nits"].delete_many({})
    result = await db["nits"].insert_many(nits_data)

    print(f"\n{'='*60}")
    print(f"✅ Generated {len(result.inserted_ids)} NITs from real data")
    print(f"{'='*60}\n")

    for n in nits_data:
        branches = [
            f"{p['short_name']}({p['historical_record_count']})"
            for p in n["mtech_programs"]
        ]
        print(f"  {n['nit_code']} ({n['name']}): {branches}")

    if skipped:
        print(f"\n⚠️ Skipped {len(skipped)} NITs with no CSE/DA "
              f"programmes found in scraped data: {skipped}")

    # Summary: branch coverage across all NITs
    print(f"\n{'='*60}")
    print("Branch coverage summary")
    print(f"{'='*60}")
    branch_nit_count = {}
    for n in nits_data:
        for p in n["mtech_programs"]:
            branch_nit_count[p["short_name"]] = branch_nit_count.get(p["short_name"], 0) + 1

    for branch, count in sorted(branch_nit_count.items()):
        full_name = BRANCH_FULL_NAMES.get(branch, branch)
        print(f"  {branch} ({full_name}): offered at {count}/31 NITs")

    client.close()


if __name__ == "__main__":
    asyncio.run(generate_nits())