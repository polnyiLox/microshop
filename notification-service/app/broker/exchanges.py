from aio_pika.abc import AbstractRobustChannel, AbstractRobustQueue

from app.core.config import PaymentEventsExchangeSettings, OrderEventsExchangeSettings


async def declare_notification_payment_queue(
        channel: AbstractRobustChannel,
        settings: PaymentEventsExchangeSettings,
) -> AbstractRobustQueue:
    payment_events_exchange = await channel.declare_exchange(
        settings.exchange_name,
        settings.exchange_type,
        durable=True,
    )
    notification_payment_queue = await channel.declare_queue(
        settings.notification_payment_queue_name,
        durable=True,
    )
    await notification_payment_queue.bind(
        payment_events_exchange,
        routing_key=settings.payment_succeeded_routing_key
    )
    await notification_payment_queue.bind(
        payment_events_exchange,
        routing_key=settings.payment_failed_routing_key
    )
    await notification_payment_queue.bind(
        payment_events_exchange,
        routing_key=settings.payment_cancelled_routing_key
    )
    await notification_payment_queue.bind(
        payment_events_exchange,
        routing_key=settings.payment_refunded_routing_key
    )
    return notification_payment_queue


async def declare_notification_order_queue(
        channel: AbstractRobustChannel,
        settings: OrderEventsExchangeSettings,
) -> AbstractRobustQueue:
    order_events_exchange = await channel.declare_exchange(
        settings.exchange_name,
        settings.exchange_type,
        durable=True,
    )
    notification_order_queue = await channel.declare_queue(
        settings.notification_order_queue_name,
        durable=True,
    )
    await notification_order_queue.bind(
        order_events_exchange,
        routing_key=settings.order_created_routing_key
    )
    await notification_order_queue.bind(
        order_events_exchange,
        routing_key=settings.order_cancelled_routing_key
    )

    return notification_order_queue
