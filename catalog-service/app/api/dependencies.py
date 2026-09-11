from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.repositories import ProductRepository
from app.services import ProductService


async def get_product_service(
        request: Request,
        session: AsyncSession = Depends(get_session)
) -> ProductService:
    return ProductService(
        product_repo=ProductRepository(session=session),
        session=session,
        cache=request.app.state.cache,
        cache_ttl_seconds=settings.redis.ttl_seconds,
        s3_client=request.app.state.s3_client,
        s3_settings=settings.s3,
    )
