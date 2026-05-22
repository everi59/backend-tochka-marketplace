from fastapi import APIRouter

from .auth import router as auth_router
from .categories import router as categories_router
from .images import router as images_router
from .inventory import router as inventory_router
from .invoices import router as invoices_router
from .moderation import router as moderation_router
from .products import router as products_router
from .public_catalog import router as public_catalog_router
from .sellers import router as sellers_router
from .skus import router as skus_router

router = APIRouter(prefix="/b2b/api/v1")
router.include_router(auth_router)
router.include_router(sellers_router)
router.include_router(categories_router)
router.include_router(products_router)
router.include_router(skus_router)
router.include_router(invoices_router)
router.include_router(images_router)
router.include_router(public_catalog_router)
router.include_router(inventory_router)
router.include_router(moderation_router)
