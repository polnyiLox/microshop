from fastapi import APIRouter

from app.core.config import settings

from .analytics import router as analytics_router
from .auth import router as auth_router
from .catalog import router as catalog_router
from .notification import router as notification_router
from .order import router as order_router
from .payment import router as payment_router


router = APIRouter(prefix=settings.api.v1_prefix)

router.include_router(auth_router)
router.include_router(catalog_router)
router.include_router(order_router)
router.include_router(payment_router)
router.include_router(notification_router)
router.include_router(analytics_router)
