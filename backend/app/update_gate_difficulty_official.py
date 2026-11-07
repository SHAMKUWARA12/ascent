"""
ASCENT Phase 3A — Add Official GATE Qualifying Cutoffs

Updates existing gate_difficulty documents with
official qualifying cutoff marks (from IIT results).

These are DIFFERENT from the VADER sentiment scores
already in the collection. The sentiment scores measure
how students FELT about the paper. The qualifying cutoffs
are the official minimum marks to pass — a numerical
feature for the ML model.

Official sources:
2024: IISc Bangalore (gate2024.iisc.ac.in)
2025: IIT Roorkee (gate2025.iitr.ac.in)
2026: IIT Guwahati (gate2026.iitg.ac.in)

Why 4 months before CCMT is enough:
GATE results → March | CCMT starts → July
Qualifying cutoff is always published with results.
No gap problem for live prediction.
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL   = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

# Official verified qualifying cutoffs (marks out of 100)
# Source: official IIT GATE result pages
OFFICIAL_CUTOFFS = {
    2021: {
        "CS": {
            "general": 26.1,
            "obc_ews": 23.4,
            "sc_st_pwd": 17.4,
            "organising_iit": "IIT Bombay"
        }
    },
    2022: {
        "CS": {
            "general": 25.0,
            "obc_ews": 22.5,
            "sc_st_pwd": 16.6,
            "organising_iit": "IIT Kharagpur"
        }
    },
    2023: {
        "CS": {
            "general": 32.5,
            "obc_ews": 29.2,
            "sc_st_pwd": 21.6,
            "organising_iit": "IIT Kanpur"
        }
    },
    2024: {
        "CS": {
            "general": 27.6,
            "obc_ews": 24.8,
            "sc_st_pwd": 18.4,
            "organising_iit": "IISc Bangalore"
        },
        "DA": {
            "general": 38.2,
            "obc_ews": 34.3,
            "sc_st_pwd": 25.4,
            "organising_iit": "IISc Bangalore"
        }
    },
    2025: {
        "CS": {
            "general": 29.2,
            "obc_ews": 26.2,
            "sc_st_pwd": 19.4,
            "organising_iit": "IIT Roorkee"
        },
        "DA": {
            "general": 33.3,
            "obc_ews": 29.9,
            "sc_st_pwd": 22.2,
            "organising_iit": "IIT Roorkee"
        }
    },
    2026: {
        "CS": {
            "general": 30.0,
            "obc_ews": 27.0,
            "sc_st_pwd": 20.0,
            "organising_iit": "IIT Guwahati"
        },
        "DA": {
            "general": 33.0,
            "obc_ews": 29.7,
            "sc_st_pwd": 22.0,
            "organising_iit": "IIT Guwahati"
        }
    }
}


async def update_official_cutoffs():
    client = AsyncIOMotorClient(MONGODB_URL)
    db     = client[DATABASE_NAME]

    print("=" * 60)
    print("Updating gate_difficulty with official cutoffs")
    print("=" * 60)

    updated  = 0
    inserted = 0

    for year, papers in OFFICIAL_CUTOFFS.items():
        for paper, cutoffs in papers.items():

            existing = await db["gate_difficulty"].find_one(
                {"year": year}
            )

            fields_to_set = {
                "gate_paper":                    paper,
                "qualifying_cutoff_general":     cutoffs["general"],
                "qualifying_cutoff_obc_ews":     cutoffs["obc_ews"],
                "qualifying_cutoff_sc_st_pwd":   cutoffs["sc_st_pwd"],
                "organising_iit":                cutoffs["organising_iit"],
                "official_data_added":           True,
            }

            if existing:
                await db["gate_difficulty"].update_one(
                    {"year": year},
                    {"$set": fields_to_set}
                )
                updated += 1
                print(
                    f"  ✅ Updated {year} {paper} | "
                    f"Gen={cutoffs['general']} | "
                    f"OBC={cutoffs['obc_ews']} | "
                    f"SC/ST={cutoffs['sc_st_pwd']}"
                )
            else:
                # Year not in collection yet — insert fresh
                await db["gate_difficulty"].insert_one({
                    "year":  year,
                    **fields_to_set
                })
                inserted += 1
                print(
                    f"  ➕ Inserted {year} {paper} | "
                    f"Gen={cutoffs['general']} | "
                    f"OBC={cutoffs['obc_ews']} | "
                    f"SC/ST={cutoffs['sc_st_pwd']}"
                )

    total = await db["gate_difficulty"].count_documents({})

    print(f"\n{'='*60}")
    print(f"Done. Updated={updated} Inserted={inserted}")
    print(f"Total documents in gate_difficulty: {total}")
    print(f"\nVerified data now available:")
    print(f"  CS paper : 2021-2026 (6 years)")
    print(f"  DA paper : 2024-2026 (3 years)")
    print(f"\nKey relationship for ML model:")
    print(f"  2022: cutoff=25.0 (easy) → CCMT scores higher")
    print(f"  2023: cutoff=32.5 (hard) → CCMT scores lower")
    print(f"  2024: cutoff=27.6 (mod)  → CCMT scores moderate")
    print(f"  2025: cutoff=29.2 (mod)  → CCMT scores moderate")
    print(f"  2026: cutoff=30.0 (mod)  → similar to 2025")
    print(f"{'='*60}")

    client.close()


if __name__ == "__main__":
    asyncio.run(update_official_cutoffs())