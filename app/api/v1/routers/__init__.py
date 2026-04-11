from fastapi import APIRouter
#
# from app.api.v1.routers.catalog import router as catalog_router
# from app.api.v1.routers.categories import router as categories_router
# from app.api.v1.routers.products import router as products_router
from app.api.v1.routers.auth import router as auth_router

api_v1_router = APIRouter()
# api_v1_router.include_router(products_router)
# api_v1_router.include_router(categories_router)
# api_v1_router.include_router(catalog_router)
api_v1_router.include_router(auth_router)

__all__ = ["api_v1_router"]

