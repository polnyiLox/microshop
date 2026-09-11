from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_product_service
from app.core.config import S3Settings
from app.main import app
from app.repositories import ProductRepository
from app.services import ProductService


@pytest.mark.asyncio(loop_scope="session")
async def test_product_crud_and_inventory_flow(session: AsyncSession) -> None:
    cache = AsyncMock()
    cache.get.return_value = None
    service = ProductService(
        ProductRepository(session),
        session,
        cache,
        60,
        AsyncMock(),
        S3Settings(),
    )
    app.dependency_overrides[get_product_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            headers = {"X-User-ID": "seller-id"}
            created = await client.post("/v1/products", headers=headers, json={
                "name": "E2E product",
                "description": "description",
                "price": 300,
                "quantity": 4,
                "image": "https://images.example.com/product.png",
                "category": "test",
            })
            product_id = created.json()["id"]
            reserved = await client.post(
                f"/v1/products/{product_id}/reserve",
                params={"quantity": 2},
            )
            fetched = await client.get(f"/v1/products/{product_id}")
            deleted = await client.delete(f"/v1/products/{product_id}", headers=headers)
            missing = await client.get(f"/v1/products/{product_id}")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 201
    assert reserved.status_code == 200
    assert reserved.json()["quantity"] == 2
    assert fetched.json()["quantity"] == 2
    assert deleted.status_code == 204
    assert missing.status_code == 404


@pytest.mark.asyncio(loop_scope="session")
async def test_product_update_rejects_another_seller(
    session: AsyncSession,
) -> None:
    repository = ProductRepository(session)
    cache = AsyncMock()
    cache.get.return_value = None
    service = ProductService(
        repository,
        session,
        cache,
        60,
        AsyncMock(),
        S3Settings(),
    )
    app.dependency_overrides[get_product_service] = lambda: service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            created = await client.post(
                "/v1/products",
                headers={"X-User-ID": "owner-id"},
                json={
                    "name": "Protected product",
                    "description": "description",
                    "price": 300,
                    "quantity": 4,
                    "category": "test",
                },
            )
            product_id = created.json()["id"]
            forbidden = await client.patch(
                f"/v1/products/{product_id}",
                headers={"X-User-ID": "another-seller"},
                json={"price": 1},
            )
    finally:
        app.dependency_overrides.clear()

    stored = await repository.get_by_id(product_id)
    assert created.status_code == 201
    assert forbidden.status_code == 403
    assert stored is not None
    assert stored.price == 300
