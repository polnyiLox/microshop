from fastapi import APIRouter

from app.core.config import settings

from .auth import router as auth_router
from .balance import router as balance_router
from .internal import router as internal_router


router = APIRouter(
    prefix=settings.api.v1_prefix
)
router.include_router(auth_router)
router.include_router(balance_router)
router.include_router(internal_router)
