from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Catalog: Facets"])
async def list_facets():
    return []