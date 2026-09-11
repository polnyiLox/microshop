from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routers.v1.order import create_order, require_order_owner
from app.exceptions import OrderNotFoundError
from app.schemas import OrderCreateRequest, OrderItemCreate


@pytest.mark.asyncio
async def test_create_uses_trusted_header_identity() -> None:
    service = AsyncMock()
    request = OrderCreateRequest(items=[OrderItemCreate(product_id="product-id", quantity=1)])

    await create_order(request, "trusted-user", service)

    sent = service.create_order.await_args.args[0]
    assert sent.user_id == "trusted-user"
    assert sent.items == request.items


@pytest.mark.asyncio
async def test_owner_dependency_hides_foreign_order() -> None:
    service = AsyncMock()
    service.get_order_by_id.return_value = SimpleNamespace(user_id="other-user")

    with pytest.raises(OrderNotFoundError):
        await require_order_owner("order-id", "trusted-user", service)
