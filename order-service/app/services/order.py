import json
import logging
from json import JSONDecodeError
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.broker import RabbitMQPublisher
from app.broker import KafkaProducer
from app.cache import RedisCache
from app.clients import CatalogClient
from app.core.config import (
    CatalogCommandsExchangeSettings,
    OrderEventsExchangeSettings,
    PaymentCommandsExchangeSettings, Settings,
)
from app.db.models import Order, OrderItem
from app.enums import OrderStatusEnum, OrderAnalyticsEventTypeEnum
from app.exceptions import (
    OrderNotFoundError,
    OrderItemNotFoundError,
    OrderItemAlreadyExistsError,
    OrderForbiddenToEditError,
    NotEnoughProductError,
    IncorrectOrderError,
    InvalidStatusTransitionError,
    CannotCloseEmptyOrderError,
    CatalogServiceUnavailableError,
    OwnProductOrderError,
)
from app.repositories import OrderRepository, OrderItemRepository
from app.schemas import (
    OrderItemUpdate,
    OrderItemCreate,
    OrderItemRead,
    OrderUpdateAllItems,
    OrderUpdate,
    OrderRead,
    OrderCreate,
    OrderAnalyticsEvent,
    OrderAnalyticsEventPayload,
    OrderAnalyticsItem
)


logger = logging.getLogger(__name__)


class OrderService:
    """Coordinate order persistence with catalog, payment and analytics events."""

    def __init__(
        self,
        order_repo: OrderRepository,
        order_item_repo: OrderItemRepository,
        session: AsyncSession,
        catalog_client: CatalogClient,
        publisher: RabbitMQPublisher,
        order_events_settings: OrderEventsExchangeSettings,
        catalog_commands_settings: CatalogCommandsExchangeSettings,
        payment_commands_settings: PaymentCommandsExchangeSettings,
        kafka_producer: KafkaProducer,
        redis_cache: RedisCache,
        settings: Settings,
    ) -> None:
        self._order_repo = order_repo
        self._order_item_repo = order_item_repo
        self._session = session
        self._catalog_client = catalog_client
        self._publisher = publisher
        self._order_events_settings = order_events_settings
        self._catalog_commands_settings = catalog_commands_settings
        self._payment_commands_settings = payment_commands_settings
        self._kafka_producer = kafka_producer
        self._redis_cache = redis_cache
        self._settings = settings

    async def _get_existing_order(self, order_id: str) -> Order:
        """Получить заказ из БД или выбросить ошибку"""
        order = await self._order_repo.get_by_id(order_id=order_id)
        if order is None:
            logger.warning("Order not found: order_id=%s", order_id)
            raise OrderNotFoundError()
        return order

    async def _publish_analytics_event(
        self,
        order: Order,
        event_type: OrderAnalyticsEventTypeEnum,
        previous_status: OrderStatusEnum | None = None,
    ) -> None:
        logger.debug(
            "Publishing order analytics event: order_id=%s, event_type=%s",
            order.id,
            event_type,
        )
        await self._kafka_producer.publish(
            event=OrderAnalyticsEvent(
                event_type=event_type,
                payload=OrderAnalyticsEventPayload(
                    order_id=order.id,
                    user_id=order.user_id,
                    total_amount=order.total_amount,
                    status=order.status,
                    previous_status=previous_status,
                    items=[
                        OrderAnalyticsItem.model_validate(item)
                        for item in order.items
                    ],
                ),
            )
        )
        logger.debug("Order analytics event published: order_id=%s", order.id)

    async def _get_existing_order_item(self, order_item_id: str) -> OrderItem:
        """Получить товар из БД или выбросить ошибку"""
        order_item = await self._order_item_repo.get_by_id(order_item_id=order_item_id)
        if order_item is None:
            logger.warning("Order item not found: order_item_id=%s", order_item_id)
            raise OrderItemNotFoundError()
        return order_item

    async def _recalculate_total(self, order: Order) -> None:
        """Пересчитать общую сумму заказа"""
        order.total_amount = await self._order_repo.calculate_total_amount(order.id)

    async def _reserve_product(self, product_id: str, quantity: int) -> dict:
        """Зарезервировать товар в каталоге (получает текущее количество)"""
        logger.debug(
            "Reserving catalog product: product_id=%s, quantity=%d",
            product_id,
            quantity,
        )
        try:
            product = await self._catalog_client.reserve_product(
                product_id=product_id,
                quantity=quantity
            )
            logger.debug("Catalog product reserved: product_id=%s", product_id)
            return product
        except NotEnoughProductError:
            logger.warning(
                "Insufficient product stock: product_id=%s, quantity=%d",
                product_id,
                quantity,
            )
            raise NotEnoughProductError()
        except CatalogServiceUnavailableError:
            logger.error("Catalog unavailable while reserving product: product_id=%s", product_id)
            raise CatalogServiceUnavailableError(
                f"Failed to reserve product {product_id}"
            )

    async def _release_product(self, product_id: str, quantity: int) -> None:
        """Освободить товар в каталоге (получает текущее количество)"""
        logger.debug(
            "Releasing catalog product: product_id=%s, quantity=%d",
            product_id,
            quantity,
        )
        try:
            await self._catalog_client.release_product(
                product_id=product_id,
                quantity=quantity
            )
            logger.debug("Catalog product released: product_id=%s", product_id)
        except CatalogServiceUnavailableError:
            logger.error("Catalog unavailable while releasing product: product_id=%s", product_id)
            raise CatalogServiceUnavailableError(
                f"Failed to release product {product_id}"
            )

    async def _validate_duplicate_product(self, order: Order, product_id: str) -> None:
        """Проверить, нет ли дубликата товара в заказе"""
        for item in order.items:
            if item.product_id == product_id:
                logger.warning(
                    "Duplicate product in order: order_id=%s, product_id=%s",
                    order.id,
                    product_id,
                )
                raise OrderItemAlreadyExistsError()

    @staticmethod
    def _ensure_product_is_not_owned_by_user(product: dict, user_id: str) -> None:
        if product.get("seller_id") == user_id:
            logger.warning(
                "Own product order rejected: product_id=%s, user_id=%s",
                product.get("id"),
                user_id,
            )
            raise OwnProductOrderError()

    async def _create_order_items(
            self,
            order_id: str,
            items: list[OrderItemCreate],
            products: list[dict],
    ) -> None:
        for i, item_data in enumerate(items):
            product = products[i]

            await self._order_item_repo.create(
                order_id=order_id,
                product_id=product["id"],
                seller_id=product["seller_id"],
                product_name=product["name"],
                quantity=item_data.quantity,
                unit_price=product["price"]
            )

    async def _check_products(
        self,
        items: list[OrderItemCreate],
        user_id: str,
    ) -> tuple[list[dict], int]:
        products = []
        product_ids = set()
        total_amount = 0

        for item_data in items:
            if item_data.product_id in product_ids:
                logger.warning(
                    "Duplicate product in order request: product_id=%s",
                    item_data.product_id,
                )
                raise OrderItemAlreadyExistsError()
            product_ids.add(item_data.product_id)

            product = await self._catalog_client.get_product(item_data.product_id)
            self._ensure_product_is_not_owned_by_user(product, user_id)
            if product["quantity"] < item_data.quantity:
                logger.warning(
                    "Insufficient product stock: product_id=%s, requested=%d, available=%d",
                    item_data.product_id,
                    item_data.quantity,
                    product["quantity"],
                )
                raise NotEnoughProductError()

            products.append(product)
            total_amount += item_data.quantity * product["price"]

        return products, total_amount

    async def _invalidate_order_lists(
            self,
            user_id: str,
            seller_ids: set[str],
    ) -> None:
        keys = {self._redis_cache.create_user_orders_key(user_id)}
        keys.update(
            self._redis_cache.create_seller_orders_key(seller_id)
            for seller_id in seller_ids
        )
        await self._redis_cache.delete(*keys)

    async def _invalidate_order_cache(
            self,
            order: Order,
            extra_seller_ids: set[str] | None = None,
            extra_item_ids: set[str] | None = None,
    ) -> None:
        seller_ids = {item.seller_id for item in order.items}
        seller_ids.update(extra_seller_ids or set())

        item_ids = {item.id for item in order.items}
        item_ids.update(extra_item_ids or set())

        keys = {
            order.id,
            self._redis_cache.create_order_items_key(order.id),
            *(
                self._redis_cache.create_order_items_key(order.id, item_id)
                for item_id in item_ids
            ),
        }
        await self._redis_cache.delete(*keys)
        await self._invalidate_order_lists(order.user_id, seller_ids)

    async def get_all_orders_by_user_id(self, user_id: str) -> list[OrderRead]:
        """Получить все заказы пользователя"""
        logger.debug("Getting user orders: user_id=%s", user_id)
        # Читаем из кэша
        user_orders_key = self._redis_cache.create_user_orders_key(
            user_id=user_id
        )
        cached_orders = await self._redis_cache.get(
            key=user_orders_key
        )
        if cached_orders is not None:
            logger.debug("User orders cache hit: user_id=%s", user_id)
            try:
                orders_json = json.loads(cached_orders)
                return [OrderRead.model_validate(order) for order in orders_json]
            except (JSONDecodeError, ValidationError, TypeError):
                logger.warning("Invalid user orders found in cache: user_id=%s", user_id)
                await self._redis_cache.delete(user_orders_key)
        else:
            logger.debug("User orders cache miss: user_id=%s", user_id)
        orders_orm = await self._order_repo.get_all_by_user_id(user_id=user_id)
        orders_read = [OrderRead.model_validate(order) for order in orders_orm]

        # Записываем в кэш
        await self._redis_cache.set(
            key=user_orders_key,
            value=json.dumps([order.model_dump(mode="json") for order in orders_read]),
            ttl_seconds=self._settings.redis.ttl_seconds
        )

        logger.debug("User orders loaded: user_id=%s, count=%d", user_id, len(orders_read))
        return orders_read

    async def get_all_orders_by_seller_id(self, seller_id: str) -> list[OrderRead]:
        logger.debug("Getting seller orders: seller_id=%s", seller_id)
        # Читаем из кэша
        seller_orders_key = self._redis_cache.create_seller_orders_key(
            seller_id=seller_id
        )
        cached_orders = await self._redis_cache.get(
            key=seller_orders_key
        )
        if cached_orders is not None:
            logger.debug("Seller orders cache hit: seller_id=%s", seller_id)
            try:
                orders_json = json.loads(cached_orders)
                return [OrderRead.model_validate(order) for order in orders_json]
            except (JSONDecodeError, ValidationError, TypeError):
                logger.warning("Invalid seller orders found in cache: seller_id=%s", seller_id)
                await self._redis_cache.delete(seller_orders_key)
        else:
            logger.debug("Seller orders cache miss: seller_id=%s", seller_id)

        orders = await self._order_repo.get_all_by_seller_id(seller_id=seller_id)
        result = []
        for order in orders:
            seller_items = [
                OrderItemRead.model_validate(item)
                for item in order.items
                if item.seller_id == seller_id
            ]
            order_read = OrderRead.model_validate(order).model_copy(
                update={
                    "items": seller_items,
                    "total_amount": sum(
                        item.unit_price * item.quantity for item in seller_items
                    ),
                },
            )
            result.append(order_read)

        # Записываем в кэш
        await self._redis_cache.set(
            key=seller_orders_key,
            value=json.dumps([order.model_dump(mode="json") for order in result]),
            ttl_seconds=self._settings.redis.ttl_seconds
        )

        logger.debug("Seller orders loaded: seller_id=%s, count=%d", seller_id, len(result))
        return result

    async def get_order_by_id(self, order_id: str) -> OrderRead:
        """Получить заказ по ID"""
        logger.debug("Getting order: order_id=%s", order_id)
        # Читаем из кэша
        cached_order = await self._redis_cache.get(order_id)
        if cached_order is not None:
            logger.debug("Order cache hit: order_id=%s", order_id)
            try:
                return OrderRead.model_validate_json(cached_order)
            except ValidationError:
                logger.warning("Invalid order found in cache: order_id=%s", order_id)
                await self._redis_cache.delete(order_id)
        else:
            logger.debug("Order cache miss: order_id=%s", order_id)

        order_orm = await self._get_existing_order(order_id=order_id)
        order_read = OrderRead.model_validate(order_orm)

        # Записываем в кэш
        await self._redis_cache.set(
            key=order_id,
            value=json.dumps(order_read.model_dump(mode="json")),
            ttl_seconds=self._settings.redis.ttl_seconds
        )

        return order_read

    async def create_order(self, order_data: OrderCreate) -> OrderRead:
        """Создать новый заказ с товарами"""
        logger.info(
            "Creating order: user_id=%s, items=%d",
            order_data.user_id,
            len(order_data.items),
        )
        logger.debug(
            "Order product IDs: %s",
            [item.product_id for item in order_data.items],
        )
        products, total_amount = await self._check_products(
            items=order_data.items,
            user_id=order_data.user_id,
        )

        async with self._session.begin():
            new_order = await self._order_repo.create(
                user_id=order_data.user_id,
                total_amount=total_amount
            )

            await self._create_order_items(
                order_id=new_order.id,
                items=order_data.items,
                products=products,
            )

        await self._invalidate_order_lists(
            order_data.user_id,
            {product["seller_id"] for product in products},
        )

        # Catalog резервирует товары асинхронно и сообщит результат событием.
        await self._publisher.publish(
            exchange_settings=self._catalog_commands_settings,
            routing_key=self._catalog_commands_settings.reserve_routing_key,
            event={
                "order_id": new_order.id,
                "items": [
                    {"product_id": item.product_id, "quantity": item.quantity}
                    for item in order_data.items
                ],
            },
        )
        await self._kafka_producer.publish(
            event=OrderAnalyticsEvent(
                event_type=OrderAnalyticsEventTypeEnum.CREATED,
                payload=OrderAnalyticsEventPayload(
                    order_id=new_order.id,
                    user_id=new_order.user_id,
                    total_amount=total_amount,
                    status=OrderStatusEnum.CREATED,
                    items=[
                        OrderAnalyticsItem(
                            product_id=item.product_id,
                            product_name=products[i]["name"],
                            quantity=item.quantity,
                            unit_price=products[i]["price"],
                        ) for i, item in enumerate(order_data.items)
                    ]
                )
            )
        )

        await self._session.refresh(new_order, attribute_names=["items"])
        result = OrderRead.model_validate(new_order)
        logger.info("Order created: order_id=%s, user_id=%s", new_order.id, new_order.user_id)
        return result

    async def handle_inventory_reserved(self, event: dict) -> None:
        """Запускает создание платежа только после успешного резерва."""
        logger.info("Handling inventory reservation: order_id=%s", event["order_id"])
        order = await self._get_existing_order(event["order_id"])
        if order.status != OrderStatusEnum.CREATED:
            logger.debug(
                "Ignoring inventory reservation for order status: order_id=%s, status=%s",
                order.id,
                order.status,
            )
            return

        previous_status = order.status
        order.status = OrderStatusEnum.WAITING_PAYMENT
        order.total_amount = event["total_amount"]
        await self._session.commit()
        await self._invalidate_order_cache(order)
        await self._publisher.publish(
            exchange_settings=self._payment_commands_settings,
            routing_key=self._payment_commands_settings.create_routing_key,
            event={
                "order_id": order.id,
                "user_id": order.user_id,
                "amount": order.total_amount,
            },
        )
        await self._publisher.publish(
            exchange_settings=self._order_events_settings,
            routing_key=self._order_events_settings.order_created_routing_key,
            event={
                "order_id": order.id,
                "user_id": order.user_id,
                "total_amount": order.total_amount,
            },
        )
        await self._publish_analytics_event(
            order=order,
            event_type=OrderAnalyticsEventTypeEnum.STATUS_CHANGED,
            previous_status=previous_status,
        )
        logger.info("Inventory reservation handled: order_id=%s", order.id)

    async def handle_inventory_reservation_failed(self, event: dict) -> None:
        logger.warning("Handling inventory reservation failure: order_id=%s", event["order_id"])
        order = await self._get_existing_order(event["order_id"])
        if order.status == OrderStatusEnum.CREATED:
            previous_status = order.status
            order.status = OrderStatusEnum.FAILED

            await self._session.commit()
            await self._invalidate_order_cache(order)

            await self._publish_analytics_event(
                order=order,
                event_type=OrderAnalyticsEventTypeEnum.FAILED,
                previous_status=previous_status,
            )
            logger.info("Order marked as failed: order_id=%s", order.id)

    async def handle_inventory_release_failed(self, event: dict) -> None:
        logger.warning("Handling inventory release failure: order_id=%s", event["order_id"])
        order = await self._get_existing_order(event["order_id"])
        if order.status in OrderStatusEnum.active_statuses():
            previous_status = order.status
            order.status = OrderStatusEnum.FAILED

            await self._session.commit()
            await self._invalidate_order_cache(order)

            await self._publish_analytics_event(
                order=order,
                event_type=OrderAnalyticsEventTypeEnum.FAILED,
                previous_status=previous_status,
            )
            logger.info("Order marked as failed: order_id=%s", order.id)

    async def handle_payment_created(self, event: dict) -> None:
        logger.info("Handling payment creation: order_id=%s", event["order_id"])
        await self.update_order(
            order_id=event["order_id"],
            update_data=OrderUpdate(status=OrderStatusEnum.WAITING_PAYMENT),
        )

    async def handle_payment_succeeded(self, event: dict) -> None:
        logger.info("Handling successful payment: order_id=%s", event["order_id"])
        order = await self._get_existing_order(event["order_id"])
        previous_status = order.status
        if order.status == OrderStatusEnum.WAITING_PAYMENT:
            order.status = OrderStatusEnum.PAID

            await self._session.commit()
            await self._invalidate_order_cache(order)
        elif order.status != OrderStatusEnum.PAID:
            logger.warning(
                "Ignoring successful payment for order status: order_id=%s, status=%s",
                order.id,
                order.status,
            )
            return

        await self._publisher.publish(
            exchange_settings=self._catalog_commands_settings,
            routing_key=self._catalog_commands_settings.confirm_routing_key,
            event={
                "event_id": str(uuid4()),
                "order_id": order.id,
                "items": [
                    {
                        "product_id": item.product_id,
                        "quantity": item.quantity,
                    }
                    for item in order.items
                ],
            },
        )
        if order.status != previous_status:
            await self._publish_analytics_event(
                order=order,
                event_type=OrderAnalyticsEventTypeEnum.STATUS_CHANGED,
                previous_status=previous_status,
            )
        logger.info("Successful payment handled: order_id=%s", order.id)

    async def handle_payment_unsucceeded(self, event: dict) -> None:
        logger.info("Handling unsuccessful payment: order_id=%s", event["order_id"])
        await self.update_order(
            order_id=event["order_id"],
            update_data=OrderUpdate(status=OrderStatusEnum.WAITING_PAYMENT),
        )

    async def handle_payment_failed(self, event: dict) -> None:
        await self.handle_payment_unsucceeded(event)

    async def handle_payment_cancelled(self, event: dict) -> None:
        order = await self._get_existing_order(event["order_id"])
        if order.status != OrderStatusEnum.CANCELLED:
            await self.handle_payment_unsucceeded(event)

    async def handle_payment_refunded(self, event: dict) -> None:
        logger.info("Handling payment refund: order_id=%s", event["order_id"])
        order = await self._get_existing_order(event["order_id"])
        if order.status != OrderStatusEnum.PAID:
            logger.warning(
                "Ignoring refund for unpaid order: order_id=%s, status=%s",
                order.id,
                order.status,
            )
            return

        previous_status = order.status
        for item in order.items:
            await self._release_product(item.product_id, item.quantity)
        order.status = OrderStatusEnum.CANCELLED
        await self._session.commit()
        await self._invalidate_order_cache(order)
        await self._publisher.publish(
            exchange_settings=self._order_events_settings,
            routing_key=self._order_events_settings.order_cancelled_routing_key,
            event={"order_id": order.id, "user_id": order.user_id},
        )
        await self._publish_analytics_event(
            order=order,
            event_type=OrderAnalyticsEventTypeEnum.CANCELLED,
            previous_status=previous_status,
        )
        logger.info("Payment refund handled: order_id=%s", order.id)

    async def update_order(
        self,
        order_id: str,
        update_data: OrderUpdate
    ) -> OrderRead:
        """Обновить статус заказа"""
        logger.info(
            "Updating order: order_id=%s, target_status=%s",
            order_id,
            update_data.status,
        )
        order = await self._get_existing_order(order_id=order_id)

        if update_data.status is not None:
            if update_data.status == order.status:
                logger.debug("Order already has requested status: order_id=%s", order_id)
                return OrderRead.model_validate(order)

            if not order.status.can_transition_to(update_data.status):
                logger.warning(
                    "Invalid order status transition: order_id=%s, current=%s, target=%s",
                    order_id,
                    order.status,
                    update_data.status,
                )
                raise InvalidStatusTransitionError(
                    order_status_from=order.status,
                    order_status_to=update_data.status
                )

            if update_data.status == OrderStatusEnum.CLOSED and not order.items:
                logger.warning("Cannot close empty order: order_id=%s", order_id)
                raise CannotCloseEmptyOrderError()

            previous_status = order.status
            order.status = update_data.status
            await self._session.commit()
            await self._invalidate_order_cache(order)

            await self._publish_analytics_event(
                order=order,
                event_type=OrderAnalyticsEventTypeEnum.STATUS_CHANGED,
                previous_status=previous_status,
            )

        result = OrderRead.model_validate(order)
        logger.info("Order updated: order_id=%s, status=%s", order.id, order.status)
        return result

    async def cancel_order(self, order_id: str) -> OrderRead:
        """
        Отменить заказ.
        - Статус → CANCELLED
        - Освободить товары
        - Отправить событие в RabbitMQ
        """
        logger.info("Cancelling order: order_id=%s", order_id)
        order = await self._get_existing_order(order_id=order_id)

        if order.status == OrderStatusEnum.PAID:
            logger.info("Requesting payment refund: order_id=%s", order_id)
            await self._publisher.publish(
                exchange_settings=self._payment_commands_settings,
                routing_key=self._payment_commands_settings.refund_routing_key,
                event={
                    "event_id": str(uuid4()),
                    "order_id": order.id,
                },
            )
            return OrderRead.model_validate(order)

        if not order.status.can_transition_to(OrderStatusEnum.CANCELLED):
            logger.warning(
                "Order cancellation rejected: order_id=%s, status=%s",
                order_id,
                order.status,
            )
            raise InvalidStatusTransitionError(
                order_status_from=order.status,
                order_status_to=OrderStatusEnum.CANCELLED
            )

        previous_status = order.status
        order.status = OrderStatusEnum.CANCELLED

        for item in order.items:
            await self._release_product(
                product_id=item.product_id,
                quantity=item.quantity
            )

        await self._publisher.publish(
            exchange_settings=self._payment_commands_settings,
            routing_key=self._payment_commands_settings.cancel_routing_key,
            event={
                "event_id": str(uuid4()),
                "order_id": order.id,
            },
        )
        await self._publisher.publish(
            exchange_settings=self._order_events_settings,
            routing_key=self._order_events_settings.order_cancelled_routing_key,
            event={"order_id": order_id, "user_id": order.user_id}
        )

        await self._session.commit()
        await self._invalidate_order_cache(order)

        await self._publish_analytics_event(
            order=order,
            event_type=OrderAnalyticsEventTypeEnum.CANCELLED,
            previous_status=previous_status,
        )

        result = OrderRead.model_validate(order)
        logger.info("Order cancelled: order_id=%s", order_id)
        return result

    async def close_order(self, order_id: str) -> OrderRead:
        """Закрыть заказ"""
        logger.info("Closing order: order_id=%s", order_id)
        order = await self._get_existing_order(order_id=order_id)

        if not order.items:
            logger.warning("Cannot close empty order: order_id=%s", order_id)
            raise CannotCloseEmptyOrderError()

        if not order.status.can_transition_to(OrderStatusEnum.CLOSED):
            logger.warning(
                "Order closure rejected: order_id=%s, status=%s",
                order_id,
                order.status,
            )
            raise InvalidStatusTransitionError(
                order_status_from=order.status,
                order_status_to=OrderStatusEnum.CLOSED
            )

        previous_status = order.status
        order.status = OrderStatusEnum.CLOSED
        await self._session.commit()
        await self._invalidate_order_cache(order)
        await self._publish_analytics_event(
            order=order,
            event_type=OrderAnalyticsEventTypeEnum.STATUS_CHANGED,
            previous_status=previous_status,
        )

        result = OrderRead.model_validate(order)
        logger.info("Order closed: order_id=%s", order_id)
        return result

    async def get_items_by_order_id(self, order_id: str) -> list[OrderItemRead]:
        """Получить все товары заказа"""
        logger.debug("Getting order items: order_id=%s", order_id)

        # Читаем кэш
        order_items_key = self._redis_cache.create_order_items_key(
            order_id=order_id,
        )
        cached_items = await self._redis_cache.get(order_items_key)
        if cached_items is not None:
            logger.debug("Order items cache hit: order_id=%s", order_id)
            try:
                items_json = json.loads(cached_items)
                return [OrderItemRead.model_validate(item) for item in items_json]
            except (JSONDecodeError, ValidationError, TypeError):
                logger.warning("Invalid order items found in cache: order_id=%s", order_id)
                await self._redis_cache.delete(order_items_key)
        else:
            logger.debug("Order items cache miss: order_id=%s", order_id)

        await self._get_existing_order(order_id=order_id)
        items_orm = await self._order_item_repo.get_all_by_order_id(order_id=order_id)
        items_read = [OrderItemRead.model_validate(item) for item in items_orm]

        # Записываем в кэш
        await self._redis_cache.set(
            key=order_items_key,
            value=json.dumps([item_read.model_dump(mode="json") for item_read in items_read]),
            ttl_seconds=self._settings.redis.ttl_seconds
        )

        logger.debug("Order items loaded: order_id=%s, count=%d", order_id, len(items_read))
        return items_read

    async def get_item_by_id(
        self,
        order_id: str,
        order_item_id: str
    ) -> OrderItemRead:
        """Получить конкретный товар из заказа"""
        logger.debug(
            "Getting order item: order_id=%s, order_item_id=%s",
            order_id,
            order_item_id,
        )
        await self._get_existing_order(order_id=order_id)

        # Читаем данные из кэша
        order_items_key = self._redis_cache.create_order_items_key(
            order_id=order_id,
            item_id=order_item_id
        )
        cached_item = await self._redis_cache.get(order_items_key)
        if cached_item is not None:
            logger.debug("Order item cache hit: order_item_id=%s", order_item_id)
            try:
                return OrderItemRead.model_validate_json(cached_item)
            except ValidationError:
                logger.warning("Invalid order item found in cache: order_item_id=%s", order_item_id)
                await self._redis_cache.delete(order_items_key)
        else:
            logger.debug("Order item cache miss: order_item_id=%s", order_item_id)

        item_orm = await self._get_existing_order_item(order_item_id=order_item_id)
        if item_orm.order_id != order_id:
            logger.warning(
                "Order item belongs to another order: order_id=%s, order_item_id=%s",
                order_id,
                order_item_id,
            )
            raise IncorrectOrderError()
        item_read = OrderItemRead.model_validate(item_orm)

        # Записываем в кэш
        await self._redis_cache.set(
            key=order_items_key,
            value=json.dumps(item_read.model_dump(mode="json")),
            ttl_seconds=self._settings.redis.ttl_seconds
        )

        return item_read

    async def add_item_to_order(
        self,
        order_id: str,
        item_data: OrderItemCreate
    ) -> OrderItemRead:
        """Добавить новый товар в заказ"""
        logger.info(
            "Adding order item: order_id=%s, product_id=%s, quantity=%d",
            order_id,
            item_data.product_id,
            item_data.quantity,
        )
        order = await self._get_existing_order(order_id=order_id)

        if not order.status.can_edit():
            logger.warning("Order cannot be edited: order_id=%s, status=%s", order_id, order.status)
            raise OrderForbiddenToEditError(
                order_status=order.status
            )

        await self._validate_duplicate_product(order, item_data.product_id)

        product = await self._catalog_client.get_product(item_data.product_id)
        self._ensure_product_is_not_owned_by_user(product, order.user_id)
        if product["quantity"] < item_data.quantity:
            logger.warning(
                "Insufficient product stock: product_id=%s, requested=%d, available=%d",
                item_data.product_id,
                item_data.quantity,
                product["quantity"],
            )
            raise NotEnoughProductError()

        await self._reserve_product(
            product_id=item_data.product_id,
            quantity=item_data.quantity
        )

        new_order_item = await self._order_item_repo.create(
            order_id=order.id,
            product_id=product["id"],
            seller_id=product["seller_id"],
            product_name=product["name"],
            quantity=item_data.quantity,
            unit_price=product["price"]
        )

        await self._recalculate_total(order=order)
        await self._session.commit()

        await self._session.refresh(new_order_item)
        await self._invalidate_order_cache(
            order,
            extra_seller_ids={new_order_item.seller_id},
            extra_item_ids={new_order_item.id},
        )
        result = OrderItemRead.model_validate(new_order_item)
        logger.info("Order item added: order_id=%s, order_item_id=%s", order_id, result.id)
        return result

    async def update_item_in_order(
        self,
        order_id: str,
        order_item_id: str,
        update_data: OrderItemUpdate
    ) -> OrderItemRead:
        """Обновить товар в заказе (количество)"""
        logger.info(
            "Updating order item: order_id=%s, order_item_id=%s, quantity=%s",
            order_id,
            order_item_id,
            update_data.quantity,
        )
        order = await self._get_existing_order(order_id=order_id)

        if not order.status.can_edit():
            logger.warning("Order cannot be edited: order_id=%s, status=%s", order_id, order.status)
            raise OrderForbiddenToEditError(
                order_status=order.status
            )

        item = await self._get_existing_order_item(order_item_id=order_item_id)
        if item.order_id != order_id:
            logger.warning(
                "Order item belongs to another order: order_id=%s, order_item_id=%s",
                order_id,
                order_item_id,
            )
            raise IncorrectOrderError()

        if update_data.quantity is None:
            return OrderItemRead.model_validate(item)

        if update_data.quantity > item.quantity:
            additional_quantity = update_data.quantity - item.quantity
            product = await self._catalog_client.get_product(item.product_id)
            self._ensure_product_is_not_owned_by_user(product, order.user_id)
            if product["quantity"] < additional_quantity:
                logger.warning(
                    "Insufficient product stock: product_id=%s, requested=%d, available=%d",
                    item.product_id,
                    additional_quantity,
                    product["quantity"],
                )
                raise NotEnoughProductError()
            await self._reserve_product(
                product_id=item.product_id,
                quantity=additional_quantity
            )
        elif update_data.quantity < item.quantity:
            released_quantity = item.quantity - update_data.quantity
            await self._release_product(
                product_id=item.product_id,
                quantity=released_quantity
            )

        item.quantity = update_data.quantity
        await self._recalculate_total(order=order)
        await self._session.commit()

        await self._session.refresh(item)
        await self._invalidate_order_cache(order)
        result = OrderItemRead.model_validate(item)
        logger.info("Order item updated: order_id=%s, order_item_id=%s", order_id, order_item_id)
        return result

    async def remove_item_from_order(
        self,
        order_id: str,
        order_item_id: str
    ) -> None:
        """Удалить товар из заказа"""
        logger.info("Removing order item: order_id=%s, order_item_id=%s", order_id, order_item_id)
        order = await self._get_existing_order(order_id=order_id)

        if not order.status.can_edit():
            logger.warning("Order cannot be edited: order_id=%s, status=%s", order_id, order.status)
            raise OrderForbiddenToEditError(
                order_status=order.status
            )

        item = await self._get_existing_order_item(order_item_id=order_item_id)
        if item.order_id != order_id:
            logger.warning(
                "Order item belongs to another order: order_id=%s, order_item_id=%s",
                order_id,
                order_item_id,
            )
            raise IncorrectOrderError()

        await self._release_product(
            product_id=item.product_id,
            quantity=item.quantity
        )

        await self._order_item_repo.delete(item)
        await self._recalculate_total(order=order)
        await self._session.commit()
        await self._invalidate_order_cache(
            order,
            extra_seller_ids={item.seller_id},
            extra_item_ids={item.id},
        )
        logger.info("Order item removed: order_id=%s, order_item_id=%s", order_id, order_item_id)

    async def update_all_items(
        self,
        order_id: str,
        items_data: OrderUpdateAllItems
    ) -> OrderRead:
        """Заменить все товары в заказе новым списком"""
        logger.info("Replacing order items: order_id=%s, items=%d", order_id, len(items_data.items))
        order = await self._get_existing_order(order_id=order_id)

        if not order.status.can_edit():
            logger.warning("Order cannot be edited: order_id=%s, status=%s", order_id, order.status)
            raise OrderForbiddenToEditError(
                order_status=order.status
            )

        old_seller_ids = {item.seller_id for item in order.items}
        old_item_ids = {item.id for item in order.items}
        old_inventory = [
            (item.product_id, item.quantity)
            for item in order.items
        ]
        released_old: list[tuple[str, int]] = []
        reserved_new: list[tuple[str, int]] = []

        try:
            # Старые резервы освобождаются до проверки, чтобы при замене того же
            # товара каталог видел всё доступное для этого заказа количество.
            for product_id, quantity in old_inventory:
                await self._release_product(product_id, quantity)
                released_old.append((product_id, quantity))

            products, total_amount = await self._check_products(
                items=items_data.items,
                user_id=order.user_id,
            )
            for item in items_data.items:
                await self._reserve_product(item.product_id, item.quantity)
                reserved_new.append((item.product_id, item.quantity))

            await self._order_item_repo.delete_all_by_order_id(order_id)
            await self._create_order_items(
                order_id=order_id,
                items=items_data.items,
                products=products,
            )

            order.total_amount = total_amount
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            # RabbitMQ/outbox здесь не нужны: для синхронной замены достаточно
            # компенсировать уже выполненные операции каталога.
            for product_id, quantity in reversed(reserved_new):
                try:
                    await self._release_product(product_id, quantity)
                except Exception:
                    logger.exception(
                        "Failed to release replacement inventory: product_id=%s",
                        product_id,
                    )
            for product_id, quantity in released_old:
                try:
                    await self._reserve_product(product_id, quantity)
                except Exception:
                    logger.exception(
                        "Failed to restore previous inventory: product_id=%s",
                        product_id,
                    )
            raise

        await self._session.refresh(order, attribute_names=["items"])
        await self._invalidate_order_cache(
            order,
            extra_seller_ids=old_seller_ids,
            extra_item_ids=old_item_ids,
        )
        result = OrderRead.model_validate(order)
        logger.info("Order items replaced: order_id=%s, items=%d", order_id, len(result.items))
        return result
