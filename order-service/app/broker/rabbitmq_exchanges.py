from aio_pika.abc import (
    AbstractRobustChannel,
    AbstractRobustExchange,
    AbstractRobustQueue
)

from app.core.config import (
    CatalogEventsExchangeSettings,
    ExchangeSettings,
    PaymentEventsExchangeSettings,
)


async def declare_exchange(
    channel: AbstractRobustChannel,
    exchange_settings: ExchangeSettings,
) -> AbstractRobustExchange:
    return await channel.declare_exchange(
        exchange_settings.exchange_name,
        exchange_settings.exchange_type,
        durable=True,
    )


async def declare_order_payment_queue(
    channel: AbstractRobustChannel,
    exchange_settings: PaymentEventsExchangeSettings,
) -> AbstractRobustQueue:
    payment_events_exchange = await declare_exchange(channel, exchange_settings)
    order_payment_queue = await channel.declare_queue(
        exchange_settings.queue_name,
        durable=True,
    )

    await order_payment_queue.bind(
        payment_events_exchange,
        routing_key=exchange_settings.payment_created_routing_key
    )
    await order_payment_queue.bind(
        payment_events_exchange,
        routing_key=exchange_settings.payment_succeeded_routing_key
    )
    await order_payment_queue.bind(
        payment_events_exchange,
        routing_key=exchange_settings.payment_failed_routing_key
    )
    await order_payment_queue.bind(
        payment_events_exchange,
        routing_key=exchange_settings.payment_cancelled_routing_key
    )
    await order_payment_queue.bind(
        payment_events_exchange,
        routing_key=exchange_settings.payment_refunded_routing_key,
    )

    return order_payment_queue


async def declare_order_catalog_queue(
    channel: AbstractRobustChannel,
    exchange_settings: CatalogEventsExchangeSettings,
) -> AbstractRobustQueue:
    catalog_events_exchange = await declare_exchange(channel, exchange_settings)
    order_catalog_queue = await channel.declare_queue(
        exchange_settings.queue_name,
        durable=True,
    )
    await order_catalog_queue.bind(
        catalog_events_exchange,
        routing_key=exchange_settings.reserved_routing_key,
    )
    await order_catalog_queue.bind(
        catalog_events_exchange,
        routing_key=exchange_settings.reservation_failed_routing_key,
    )
    await order_catalog_queue.bind(
        catalog_events_exchange,
        routing_key=exchange_settings.released_routing_key,
    )
    await order_catalog_queue.bind(
        catalog_events_exchange,
        routing_key=exchange_settings.release_failed_routing_key,
    )
    return order_catalog_queue
