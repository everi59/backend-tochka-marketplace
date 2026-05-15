from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Catalog: Categories"])
async def list_categories():
    return []