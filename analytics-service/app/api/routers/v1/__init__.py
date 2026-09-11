from fastapi import APIRouter

from app.core.config import settings

from .analytics import router as analytics_router


router = APIRouter(prefix=settings.api.v1_prefix)
router.include_router(analytics_router)
