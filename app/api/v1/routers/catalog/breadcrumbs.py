from fastapi import APIRouter

router = APIRouter()

@router.get("/", tags=["Catalog: Breadcrumbs"])
async def list_breadcrumbs():
    return []