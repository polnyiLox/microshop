from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_current_user_id, get_order_service
from app.exceptions import OrderNotFoundError
from app.schemas import (
    OrderCreate,
    OrderCreateRequest,
    OrderItemCreate,
    OrderItemRead,
    OrderItemUpdate,
    OrderRead,
    OrderUpdate,
    OrderUpdateAllItems,
)
from app.services.order import OrderService


router = APIRouter(prefix="/orders", tags=["Заказы"])


async def require_order_owner(
    order_id: str,
    current_user_id: str = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> str:
    order = await service.get_order_by_id(order_id)
    if order.user_id != current_user_id:
        raise OrderNotFoundError()
    return current_user_id


@router.get("", response_model=list[OrderRead])
async def get_orders(
    current_user_id: str = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> list[OrderRead]:
    return await service.get_all_orders_by_user_id(current_user_id)


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreateRequest,
    current_user_id: str = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    trusted_order_data = OrderCreate(
        user_id=current_user_id,
        items=order_data.items,
    )
    return await service.create_order(trusted_order_data)


@router.get("/sales", response_model=list[OrderRead])
async def get_sales(
    current_user_id: str = Depends(get_current_user_id),
    service: OrderService = Depends(get_order_service),
) -> list[OrderRead]:
    return await service.get_all_orders_by_seller_id(current_user_id)


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: str,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    return await service.get_order_by_id(order_id)


@router.patch("/{order_id}", response_model=OrderRead)
async def update_order(
    order_id: str,
    update_data: OrderUpdate,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    return await service.update_order(order_id, update_data)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel_order(
    order_id: str,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    return await service.cancel_order(order_id)


@router.post("/{order_id}/close", response_model=OrderRead)
async def close_order(
    order_id: str,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    return await service.close_order(order_id)


@router.get("/{order_id}/items", response_model=list[OrderItemRead])
async def get_items(
    order_id: str,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> list[OrderItemRead]:
    return await service.get_items_by_order_id(order_id)


@router.post("/{order_id}/items", response_model=OrderItemRead, status_code=status.HTTP_201_CREATED)
async def add_item(
    order_id: str,
    item_data: OrderItemCreate,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderItemRead:
    return await service.add_item_to_order(order_id, item_data)


@router.put("/{order_id}/items", response_model=OrderRead)
async def replace_items(
    order_id: str,
    items_data: OrderUpdateAllItems,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderRead:
    return await service.update_all_items(order_id, items_data)


@router.get("/{order_id}/items/{order_item_id}", response_model=OrderItemRead)
async def get_item(
    order_id: str,
    order_item_id: str,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderItemRead:
    return await service.get_item_by_id(order_id, order_item_id)


@router.patch("/{order_id}/items/{order_item_id}", response_model=OrderItemRead)
async def update_item(
    order_id: str,
    order_item_id: str,
    update_data: OrderItemUpdate,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> OrderItemRead:
    return await service.update_item_in_order(order_id, order_item_id, update_data)


@router.delete("/{order_id}/items/{order_item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_item(
    order_id: str,
    order_item_id: str,
    current_user_id: str = Depends(require_order_owner),
    service: OrderService = Depends(get_order_service),
) -> Response:
    await service.remove_item_from_order(order_id, order_item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
