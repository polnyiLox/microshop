from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from fastapi import UploadFile

from app.api.routers.v1.product import create_product, reserve_product, upload_product_image
from app.schemas import ProductCreate, ProductCreateRequest


@pytest.mark.asyncio
async def test_create_endpoint_delegates_to_service() -> None:
    service = AsyncMock()
    data = ProductCreateRequest(
        name="Test product",
        description="description",
        price=100,
        quantity=3,
        image="https://images.example.com/product.png",
        category="test",
    )

    await create_product(data, "seller-id", service)

    service.create_product.assert_awaited_once_with(
        product_data=ProductCreate(**data.model_dump(), seller_id="seller-id"),
    )


@pytest.mark.asyncio
async def test_reserve_endpoint_passes_validated_quantity() -> None:
    service = AsyncMock()

    await reserve_product("product-id", 2, service)

    service.reserve_product.assert_awaited_once_with("product-id", 2)


@pytest.mark.asyncio
async def test_image_endpoint_reads_file_for_service() -> None:
    service = AsyncMock()
    image = UploadFile(
        file=BytesIO(b"image-content"),
        filename="product.png",
        headers={"content-type": "image/png"},
    )

    await upload_product_image("product-id", image, "seller-id", service)

    service.upload_product_image.assert_awaited_once_with(
        product_id="product-id",
        seller_id="seller-id",
        content=b"image-content",
        content_type="image/png",
    )
