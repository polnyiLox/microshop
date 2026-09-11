from fastapi import APIRouter

from app.core.config import settings

from .payment import router as payment_router


router = APIRouter(prefix=settings.api.v1_prefix)
router.include_router(payment_router)
