from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config import S3Settings
from app.exceptions import NotEnoughProductError, ProductImageError, ProductNotFoundError
from app.schemas import ProductCreate, ProductRead
from app.services import ProductService


def product(product_id: str = "product-id", quantity: int = 5) -> SimpleNamespace:
    return SimpleNamespace(
        id=product_id,
        name="Test product",
        description="description",
        price=250,
        quantity=quantity,
        image_key="https://images.example.com/product.png",
        category="test",
        seller_id="seller-id",
    )


def product_service(
    repository: AsyncMock,
    session: AsyncMock,
) -> tuple[ProductService, AsyncMock, AsyncMock]:
    cache = AsyncMock()
    cache.get.return_value = None
    s3_client = AsyncMock()
    s3_client.generate_presigned_image_url.return_value = "http://localhost/image"
    return (
        ProductService(
            repository,
            session,
            cache,
            60,
            s3_client,
            S3Settings(),
        ),
        cache,
        s3_client,
    )


@pytest.mark.asyncio
async def test_create_product_delegates_and_commits() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    repository.create.return_value = product()
    service, _, _ = product_service(repository, session)
    data = ProductCreate(
        name="Test product",
        description="description",
        price=250,
        quantity=5,
        image="https://images.example.com/product.png",
        category="test",
        seller_id="seller-id",
    )

    result = await service.create_product(data)

    repository.create.assert_awaited_once_with(
        name=data.name,
        description=data.description,
        price=data.price,
        quantity=data.quantity,
        image_key=data.image,
        category=data.category,
        seller_id=data.seller_id,
    )
    session.commit.assert_awaited_once()
    assert result.id == "product-id"


@pytest.mark.asyncio
async def test_reserve_products_rolls_back_partial_reservation() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    repository.reserve_product.side_effect = [product("first"), None]
    repository.get_by_id.return_value = product("second")
    service, _, _ = product_service(repository, session)

    with pytest.raises(NotEnoughProductError):
        await service.reserve_products([
            {"product_id": "first", "quantity": 1},
            {"product_id": "second", "quantity": 10},
        ])

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_reserve_product_distinguishes_missing_product() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    repository.reserve_product.return_value = None
    repository.get_by_id.return_value = None

    with pytest.raises(ProductNotFoundError):
        await product_service(repository, session)[0].reserve_product("missing", 1)


@pytest.mark.asyncio
async def test_get_product_returns_cached_value() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    service, cache, _ = product_service(repository, session)
    cache.get.return_value = ProductRead(
        id="product-id",
        name="Test product",
        description="description",
        price=250,
        quantity=5,
        image="https://images.example.com/product.png",
        category="test",
        seller_id="seller-id",
    ).model_dump_json()

    result = await service.get_product_by_id("product-id")

    assert result.id == "product-id"
    repository.get_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_product_caches_database_value() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    repository.get_by_id.return_value = product()
    service, cache, _ = product_service(repository, session)

    result = await service.get_product_by_id("product-id")

    assert result.id == "product-id"
    cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_upload_product_image_replaces_old_s3_object() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    existing_product = product()
    existing_product.image_key = "product-images/product-id/old.png"
    repository.get_by_id.return_value = existing_product
    service, cache, s3_client = product_service(repository, session)

    result = await service.upload_product_image(
        product_id="product-id",
        seller_id="seller-id",
        content=b"image-content",
        content_type="image/png",
    )

    s3_client.upload_file.assert_awaited_once()
    s3_client.delete_file.assert_awaited_once_with(
        "product-images/product-id/old.png",
    )
    session.commit.assert_awaited_once()
    cache.delete.assert_awaited_once_with("products:product-id")
    assert result.image == "http://localhost/image"


@pytest.mark.asyncio
async def test_upload_product_image_rejects_unsupported_type() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    repository.get_by_id.return_value = product()
    service, _, s3_client = product_service(repository, session)

    with pytest.raises(ProductImageError):
        await service.upload_product_image(
            product_id="product-id",
            seller_id="seller-id",
            content=b"text-content",
            content_type="text/plain",
        )

    s3_client.upload_file.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_product_image_cleans_new_object_after_commit_error() -> None:
    repository = AsyncMock()
    session = AsyncMock()
    session.commit.side_effect = RuntimeError("database error")
    repository.get_by_id.return_value = product()
    service, _, s3_client = product_service(repository, session)

    with pytest.raises(RuntimeError):
        await service.upload_product_image(
            product_id="product-id",
            seller_id="seller-id",
            content=b"image-content",
            content_type="image/webp",
        )

    session.rollback.assert_awaited_once()
    s3_client.delete_file.assert_awaited_once()
