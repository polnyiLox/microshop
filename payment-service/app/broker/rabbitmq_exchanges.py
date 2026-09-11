from aio_pika.abc import AbstractExchange, AbstractRobustChannel, AbstractRobustQueue

from app.core.config import ExchangeSettings, PaymentCommandsExchangeSettings


async def declare_exchange(
    channel: AbstractRobustChannel,
    exchange_settings: ExchangeSettings,
) -> AbstractExchange:
    return await channel.declare_exchange(
        exchange_settings.exchange_name,
        exchange_settings.exchange_type,
        durable=True,
    )


async def declare_payment_events_exchange(
    channel: AbstractRobustChannel,
    exchange_settings: ExchangeSettings,
) -> AbstractExchange:
    return await declare_exchange(channel, exchange_settings)


async def declare_payment_commands_queue(
    channel: AbstractRobustChannel,
    exchange_settings: PaymentCommandsExchangeSettings,
) -> AbstractRobustQueue:
    payment_commands_exchange = await declare_exchange(channel, exchange_settings)
    payment_commands_queue = await channel.declare_queue(
        exchange_settings.queue_name,
        durable=True,
    )
    await payment_commands_queue.bind(
        payment_commands_exchange,
        routing_key=exchange_settings.create_routing_key,
    )
    await payment_commands_queue.bind(
        payment_commands_exchange,
        routing_key=exchange_settings.cancel_routing_key,
    )
    await payment_commands_queue.bind(
        payment_commands_exchange,
        routing_key=exchange_settings.refund_routing_key,
    )
    return payment_commands_queue
