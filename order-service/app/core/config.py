from functools import lru_cache
from urllib.parse import quote

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataBaseSettings(BaseModel):
    user: str
    password: str
    host: str
    port: int
    name: str

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        database = quote(self.name, safe="")
        return (
            f"postgresql+asyncpg://{user}:{password}@"
            f"{self.host}:{self.port}/{database}"
        )


class ApiSettings(BaseModel):
    v1_prefix: str
    host: str
    port: int
    reload: bool


class LoggingSettings(BaseModel):
    level: str = "INFO"


class CatalogClientSettings(BaseModel):
    base_url: str


class RabbitMQSettings(BaseModel):
    user: str = "order_service"
    password: str = "change_me"
    host: str = "rabbitmq"
    port: int = 5672
    vhost: str = "/"

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        vhost = quote(self.vhost, safe="")
        return f"amqp://{user}:{password}@{self.host}:{self.port}/{vhost}"


class KafkaSettings(BaseModel):
    bootstrap_servers: str = "host.docker.internal:9092"
    client_id: str = "order-service"
    acks: str = "all"


class AnalyticsTopicsSettings(BaseModel):
    order_events_topic: str = "order.analytics.events"


class ExchangeSettings(BaseModel):
    exchange_name: str
    exchange_type: str = "topic"


class OrderEventsExchangeSettings(ExchangeSettings):
    exchange_name: str = "order.events"
    order_created_routing_key: str = "order.created"
    order_cancelled_routing_key: str = "order.cancelled"


class PaymentEventsExchangeSettings(ExchangeSettings):
    exchange_name: str = "payment.events"
    queue_name: str = "order.payment.queue"
    payment_created_routing_key: str = "payment.created"
    payment_succeeded_routing_key: str = "payment.succeeded"
    payment_failed_routing_key: str = "payment.failed"
    payment_cancelled_routing_key: str = "payment.cancelled"
    payment_refunded_routing_key: str = "payment.refunded"


class CatalogCommandsExchangeSettings(ExchangeSettings):
    exchange_name: str = "catalog.commands"
    reserve_routing_key: str = "inventory.reserve"
    release_routing_key: str = "inventory.release"
    confirm_routing_key: str = "inventory.confirm"


class CatalogEventsExchangeSettings(ExchangeSettings):
    exchange_name: str = "catalog.events"
    queue_name: str = "order.catalog.queue"
    reserved_routing_key: str = "inventory.reserved"
    reservation_failed_routing_key: str = "inventory.reservation_failed"
    released_routing_key: str = "inventory.released"
    release_failed_routing_key: str = "inventory.release_failed"


class PaymentCommandsExchangeSettings(ExchangeSettings):
    exchange_name: str = "payment.commands"
    create_routing_key: str = "payment.create"
    cancel_routing_key: str = "payment.cancel"
    refund_routing_key: str = "payment.refund"


class RedisSettings(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ttl_seconds: int = 3600
    key_prefix: str = "order"
    user_orders_key: str = "user:"
    seller_orders_key: str = "seller:"
    order_items_key: str = ":items:"

    @property
    def url(self) -> str:
        credentials = ""
        if self.password is not None:
            credentials += f":{quote(self.password, safe='')}@"
        return f"redis://{credentials}{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    db: DataBaseSettings
    api: ApiSettings
    catalog_client: CatalogClientSettings
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    kafka: KafkaSettings = KafkaSettings()
    analytics_topics: AnalyticsTopicsSettings = AnalyticsTopicsSettings()
    order_events_ex: OrderEventsExchangeSettings = OrderEventsExchangeSettings()
    payment_events_ex: PaymentEventsExchangeSettings = PaymentEventsExchangeSettings()
    catalog_commands_ex: CatalogCommandsExchangeSettings = CatalogCommandsExchangeSettings()
    catalog_events_ex: CatalogEventsExchangeSettings = CatalogEventsExchangeSettings()
    payment_commands_ex: PaymentCommandsExchangeSettings = PaymentCommandsExchangeSettings()
    redis: RedisSettings = RedisSettings()
    logging: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
