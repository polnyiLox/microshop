from fastapi import APIRouter

from app.core.config import settings

from .notification import router as notification_router
from .websocket import router as websocket_router


router = APIRouter(
    prefix=settings.api.v1_prefix
)
router.include_router(notification_router)
router.include_router(websocket_router)
