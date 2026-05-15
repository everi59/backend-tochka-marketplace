from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Catalog: Products"])
async def list_products():
    return []