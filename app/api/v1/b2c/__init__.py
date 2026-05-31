from fastapi import APIRouter

from .addresses import router as addresses_router
from .auth import router as auth_router
from .buyers import router as buyers_router
from .cart import router as cart_router
from .catalog import router as catalog_router
from .events import router as events_router
from .favorites import router as favorites_router
from .notifications import router as notifications_router
from .orders import router as orders_router
from .payment_methods import router as payment_methods_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(buyers_router)
router.include_router(addresses_router)
router.include_router(payment_methods_router)
router.include_router(catalog_router)
router.include_router(cart_router)
router.include_router(favorites_router)
router.include_router(orders_router)
router.include_router(notifications_router)
router.include_router(events_router)
