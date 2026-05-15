from fastapi import APIRouter

# Import catalog router only – other routers are not yet defined
from app.api.v1.routers.catalog import router as catalog_router

api_v1_router = APIRouter()
api_v1_router.include_router(catalog_router, prefix="/catalog")

__all__ = ["api_v1_router"]

