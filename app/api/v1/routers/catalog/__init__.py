from fastapi import APIRouter

# Main router for catalog related endpoints
router = APIRouter()

# Import sub-routers (empty for now – placeholder)
from .categories import router as categories_router
from .breadcrumbs import router as breadcrumbs_router
from .products import router as products_router
from .facets import router as facets_router

# Include sub‑routers with appropriate prefixes
router.include_router(categories_router, prefix="/categories")
router.include_router(breadcrumbs_router, prefix="/breadcrumbs")
router.include_router(products_router, prefix="/products")
router.include_router(facets_router, prefix="/facets")

__all__ = ["router"]