from fastapi import APIRouter
from app.database import get_db

router = APIRouter()

@router.get("/nits")
async def get_all_nits():
    db = get_db()
    nits = await db["nits"].find(
        {},
        {"_id": 0}
    ).to_list(length=100)
    return {
        "total": len(nits),
        "nits": nits
    }

@router.get("/nits/{nit_code}")
async def get_nit_by_code(nit_code: str):
    db = get_db()
    nit = await db["nits"].find_one(
        {"nit_code": nit_code.upper()},
        {"_id": 0}
    )
    if not nit:
        return {"error": f"NIT with code {nit_code} not found"}
    return nit