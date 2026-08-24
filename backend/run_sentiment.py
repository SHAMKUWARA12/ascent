import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.sentiment import calculate_gate_difficulty, calculate_nit_quality

MONGODB_URL   = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

NITS = [
    {"code": "NITSLR", "name": "NIT Silchar"},
    {"code": "NITRK",  "name": "NIT Rourkela"},
    {"code": "NITT",   "name": "NIT Trichy"},
    {"code": "NITW",   "name": "NIT Warangal"},
    {"code": "NITC",   "name": "NIT Calicut"},
]

GATE_YEARS = [2024, 2025, 2026]

async def run():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    print("\n" + "="*50)
    print("STEP 1: Collecting GATE difficulty scores")
    print("="*50)

    await db["gate_difficulty"].delete_many({})

    for year in GATE_YEARS:
        print(f"\nAnalysing GATE {year}...")
        result = calculate_gate_difficulty(year)
        await db["gate_difficulty"].insert_one(result)
        print(f"  GATE {year}: {result['difficulty_score']}/10 — {result['label']}")
        print(f"  Posts analysed: {result['posts_analysed']}")

    print("\n" + "="*50)
    print("STEP 2: Collecting NIT quality scores")
    print("="*50)

    await db["nit_sentiment"].delete_many({})

    for nit in NITS:
        print(f"\nAnalysing {nit['name']}...")
        result = calculate_nit_quality(nit["name"], nit["code"])
        await db["nit_sentiment"].insert_one(result)
        print(f"  Overall: {result['overall_score']}/10 — {result['label']}")
        print(f"  Posts analysed: {result['posts_analysed']}")

    gate_count = await db["gate_difficulty"].count_documents({})
    nit_count  = await db["nit_sentiment"].count_documents({})

    print("\n" + "="*50)
    print("SENTIMENT PIPELINE COMPLETE")
    print(f"GATE difficulty records: {gate_count}")
    print(f"NIT sentiment records:   {nit_count}")
    print("="*50)

    client.close()

if __name__ == "__main__":
    asyncio.run(run())