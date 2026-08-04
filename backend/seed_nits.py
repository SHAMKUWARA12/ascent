import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "ascent_db"

nits_data = [
    {
        "nit_code": "NITSLR",
        "name": "NIT Silchar",
        "location": "Silchar, Assam",
        "state": "Assam",
        "region": "East India",
        "nirf_rank": 48,
        "established": 1967,
        "mtech_programs": [
            {
                "program_id": "NITSLR_CSE",
                "official_name": "M.Tech in Computer Science & Engineering",
                "short_name": "CSE",
                "gate_papers": ["CS"],
                "seats": {"UR": 9, "OBC": 5, "SC": 2, "ST": 1, "EWS": 1},
                "fee_annual": 70000,
                "has_hostel": True
            }
        ]
    },
    {
        "nit_code": "NITRK",
        "name": "NIT Rourkela",
        "location": "Rourkela, Odisha",
        "state": "Odisha",
        "region": "East India",
        "nirf_rank": 9,
        "established": 1961,
        "mtech_programs": [
            {
                "program_id": "NITRK_CSE",
                "official_name": "M.Tech in Computer Science & Engineering",
                "short_name": "CSE",
                "gate_papers": ["CS"],
                "seats": {"UR": 10, "OBC": 5, "SC": 3, "ST": 1, "EWS": 1},
                "fee_annual": 110000,
                "has_hostel": True
            }
        ]
    },
    {
        "nit_code": "NITT",
        "name": "NIT Trichy",
        "location": "Tiruchirappalli, Tamil Nadu",
        "state": "Tamil Nadu",
        "region": "South India",
        "nirf_rank": 8,
        "established": 1964,
        "mtech_programs": [
            {
                "program_id": "NITT_CSE",
                "official_name": "M.Tech in Computer Science & Engineering",
                "short_name": "CSE",
                "gate_papers": ["CS"],
                "seats": {"UR": 9, "OBC": 5, "SC": 2, "ST": 1, "EWS": 1},
                "fee_annual": 90000,
                "has_hostel": True
            }
        ]
    },
    {
        "nit_code": "NITW",
        "name": "NIT Warangal",
        "location": "Warangal, Telangana",
        "state": "Telangana",
        "region": "South India",
        "nirf_rank": 5,
        "established": 1959,
        "mtech_programs": [
            {
                "program_id": "NITW_CSE",
                "official_name": "M.Tech in Computer Science & Engineering",
                "short_name": "CSE",
                "gate_papers": ["CS"],
                "seats": {"UR": 9, "OBC": 5, "SC": 2, "ST": 1, "EWS": 1},
                "fee_annual": 95000,
                "has_hostel": True
            }
        ]
    },
    {
        "nit_code": "NITC",
        "name": "NIT Calicut",
        "location": "Calicut, Kerala",
        "state": "Kerala",
        "region": "South India",
        "nirf_rank": 12,
        "established": 1961,
        "mtech_programs": [
            {
                "program_id": "NITC_CSE",
                "official_name": "M.Tech in Computer Science & Engineering",
                "short_name": "CSE",
                "gate_papers": ["CS"],
                "seats": {"UR": 9, "OBC": 5, "SC": 2, "ST": 1, "EWS": 1},
                "fee_annual": 85000,
                "has_hostel": True
            }
        ]
    }
]

async def seed():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    await db["nits"].delete_many({})
    result = await db["nits"].insert_many(nits_data)
    print(f"✅ Seeded {len(result.inserted_ids)} NITs into ascent_db")
    client.close()

if __name__ == "__main__":
    asyncio.run(seed())