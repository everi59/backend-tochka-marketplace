from fastapi import APIRouter

from .categories import router as categories_router
from .images import router as images_router
from .inventory import router as inventory_router
from .invoices import router as invoices_router
from .moderation import router as moderation_router
from .products import router as products_router
from .public_catalog import router as public_catalog_router
from .sellers import router as sellers_router
from .skus import router as skus_router

router = APIRouter()
for prefix in ("/api/v1",):
    router.include_router(sellers_router, prefix=prefix)
    router.include_router(categories_router, prefix=prefix)
    router.include_router(products_router, prefix=prefix)
    router.include_router(skus_router, prefix=prefix)
    router.include_router(invoices_router, prefix=prefix)
    router.include_router(images_router, prefix=prefix)
    router.include_router(public_catalog_router, prefix=prefix)
    router.include_router(inventory_router, prefix=prefix)
    router.include_router(moderation_router, prefix=prefix)
