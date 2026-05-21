from fastapi import APIRouter

from app.api.v1.routers.catalog.products import router as products_router
from app.api.v1.routers.catalog.categories import router as categories_router
from app.api.v1.routers.catalog.facets import router as facets_router

from app.api.v1.routers.seller.products import router as seller_products_router
from app.api.v1.routers.seller.skus import router as seller_skus_router
from app.api.v1.routers.seller.invoices import router as seller_invoices_router

api_v1_router = APIRouter()

api_v1_router.include_router(products_router)
api_v1_router.include_router(categories_router)
api_v1_router.include_router(facets_router)

api_v1_router.include_router(seller_products_router)
api_v1_router.include_router(seller_skus_router)
api_v1_router.include_router(seller_invoices_router)


__all__ = ["api_v1_router"]
