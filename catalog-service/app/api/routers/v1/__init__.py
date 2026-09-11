from fastapi import APIRouter

from app.core.config import settings

from .product import router as product_router


router = APIRouter(
    prefix=settings.api.v1_prefix
)
router.include_router(product_router)
