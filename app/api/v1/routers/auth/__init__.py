from fastapi import APIRouter

from app.api.v1.routers.auth.auth import router as auth_router
from app.api.v1.routers.auth.register import router as register_router

router = APIRouter(prefix="/auth", tags=["Auth"])

router.include_router(auth_router)
router.include_router(register_router)

__all__ = ['router']