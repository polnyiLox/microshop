from aio_pika.abc import AbstractRobustChannel, AbstractRobustExchange, AbstractRobustQueue

from app.core.config import CatalogCommandsExchangeSettings, ExchangeSettings


async def declare_exchange(
    channel: AbstractRobustChannel,
    exchange_settings: ExchangeSettings,
) -> AbstractRobustExchange:
    return await channel.declare_exchange(
        exchange_settings.exchange_name,
        exchange_settings.exchange_type,
        durable=True,
    )


async def declare_catalog_commands_queue(
    channel: AbstractRobustChannel,
    exchange_settings: CatalogCommandsExchangeSettings,
) -> AbstractRobustQueue:
    commands_exchange = await declare_exchange(channel, exchange_settings)
    commands_queue = await channel.declare_queue(
        exchange_settings.queue_name,
        durable=True,
    )
    await commands_queue.bind(
        commands_exchange,
        routing_key=exchange_settings.reserve_routing_key,
    )
    await commands_queue.bind(
        commands_exchange,
        routing_key=exchange_settings.release_routing_key,
    )
    await commands_queue.bind(
        commands_exchange,
        routing_key=exchange_settings.confirm_routing_key,
    )
    return commands_queue
