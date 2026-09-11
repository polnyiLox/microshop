import logging
from typing import TYPE_CHECKING

from app.core.config import CatalogEventsExchangeSettings
from app.exceptions import NotEnoughProductError, ProductNotFoundError

from .product import ProductService

if TYPE_CHECKING:
    from app.broker.publisher import RabbitMQPublisher


logger = logging.getLogger(__name__)


class InventoryService:
    """Обрабатывает команды жизненного цикла товарного резерва."""

    def __init__(
        self,
        product_service: ProductService,
        publisher: "RabbitMQPublisher",
        events_settings: CatalogEventsExchangeSettings,
    ) -> None:
        self._product_service = product_service
        self._publisher = publisher
        self._events_settings = events_settings

    async def reserve(self, command: dict) -> None:
        logger.info("Processing inventory reservation: order_id=%s", command["order_id"])
        try:
            products = await self._product_service.reserve_products(command["items"])
            reserved_items = [
                {
                    "product_id": product.id,
                    "quantity": item["quantity"],
                    "unit_price": product.price,
                }
                for item, product in zip(command["items"], products, strict=True)
            ]

            await self._publisher.publish(
                self._events_settings.reserved_routing_key,
                {
                    "order_id": command["order_id"],
                    "items": reserved_items,
                    "total_amount": sum([item["quantity"] * item["unit_price"] for item in reserved_items]),
                },
            )
            logger.info("Inventory reserved: order_id=%s", command["order_id"])
        except (NotEnoughProductError, ProductNotFoundError) as error:
            logger.warning("Inventory reservation rejected: order_id=%s", command["order_id"])
            await self._publisher.publish(
                self._events_settings.reservation_failed_routing_key,
                {
                    "order_id": command["order_id"],
                    "reason": error.detail,
                },
            )

    async def release(self, command: dict) -> None:
        logger.info("Processing inventory release: order_id=%s", command["order_id"])
        try:
            await self._product_service.release_products(command["items"])
            await self._publisher.publish(
                self._events_settings.released_routing_key,
                {"order_id": command["order_id"]},
            )
            logger.info("Inventory released: order_id=%s", command["order_id"])
        except ProductNotFoundError as error:
            logger.warning("Inventory release failed: order_id=%s", command["order_id"])
            await self._publisher.publish(
                self._events_settings.release_failed_routing_key,
                {
                    "order_id": command["order_id"],
                    "reason": error.detail,
                },
            )

    async def confirm(self, command: dict) -> None:
        """Подтверждает уже списанный при резервировании остаток.

        Текущая модель каталога хранит только доступное количество: команда
        reserve уже атомарно уменьшает его. Поэтому confirm не должна повторно
        менять остаток; она проверяет состав резерва и завершает его жизненный
        цикл идемпотентно.
        """
        logger.info("Processing inventory confirmation: order_id=%s", command["order_id"])
        await self._product_service.confirm_products(command["items"])
        logger.info("Inventory confirmed: order_id=%s", command["order_id"])
