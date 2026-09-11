from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import NotEnoughProductError, ProductForbiddenError
from app.core.config import S3Settings
from app.repositories import ProductRepository
from app.schemas import ProductCreate, ProductUpdate
from app.services import ProductService


pytestmark = pytest.mark.asyncio(loop_scope="session")


async def create_product(repository: ProductRepository, suffix: str, quantity: int = 5):
    return await repository.create(
        name=f"Product {suffix}",
        description="description",
        price=100,
        quantity=quantity,
        image_key="https://images.example.com/product.png",
        category="test",
        seller_id="seller-id",
    )


async def test_repository_reserves_and_releases_atomically(session: AsyncSession) -> None:
    repository = ProductRepository(session)
    created = await create_product(repository, "repository", quantity=5)

    reserved = await repository.reserve_product(created.id, 3)
    reserved_quantity = reserved.quantity if reserved is not None else None
    rejected = await repository.reserve_product(created.id, 3)
    released = await repository.release_product(created.id, 2)

    assert reserved_quantity == 2
    assert rejected is None
    assert released is not None and released.quantity == 4


async def test_service_rolls_back_multi_product_reservation(session: AsyncSession) -> None:
    repository = ProductRepository(session)
    first = await create_product(repository, "first", quantity=2)
    second = await create_product(repository, "second", quantity=1)
    first_id, second_id = first.id, second.id
    await session.commit()
    service = ProductService(
        repository,
        session,
        AsyncMock(),
        60,
        AsyncMock(),
        S3Settings(),
    )

    with pytest.raises(NotEnoughProductError):
        await service.reserve_products([
            {"product_id": first.id, "quantity": 1},
            {"product_id": second.id, "quantity": 2},
        ])

    assert (await repository.get_by_id(first_id)).quantity == 2
    assert (await repository.get_by_id(second_id)).quantity == 1


async def test_service_persists_update_and_enforces_seller_ownership(
    session: AsyncSession,
) -> None:
    repository = ProductRepository(session)
    product = await create_product(repository, "ownership")
    await session.commit()
    service = ProductService(
        repository,
        session,
        AsyncMock(),
        60,
        AsyncMock(),
        S3Settings(),
    )

    with pytest.raises(ProductForbiddenError):
        await service.update_product(
            product.id,
            "another-seller",
            ProductUpdate(price=999),
        )

    updated = await service.update_product(
        product.id,
        "seller-id",
        ProductUpdate(price=250, quantity=8),
    )
    stored = await repository.get_by_id(product.id)

    assert updated.price == 250
    assert updated.quantity == 8
    assert stored is not None
    assert stored.price == 250
    assert stored.quantity == 8
