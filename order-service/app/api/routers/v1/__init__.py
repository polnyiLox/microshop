from fastapi import APIRouter

from app.core.config import settings

from .order import router as order_router


router = APIRouter(prefix=settings.api.v1_prefix)
router.include_router(order_router)
