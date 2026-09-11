from functools import lru_cache
from urllib.parse import quote

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoDBSettings(BaseModel):
    user: str
    password: str
    host: str
    port: int
    name: str
    auth_source: str = "admin"

    @property
    def url(self) -> str:
        user = quote(self.user, safe="")
        password = quote(self.password, safe="")
        auth_source = quote(self.auth_source, safe="")
        return (
            f"mongodb://{user}:{password}@{self.host}:{self.port}/"
            f"?authSource={auth_source}"
        )


class ApiSettings(BaseModel):
    v1_prefix: str
    host: str
    port: int
    reload: bool


class LoggingSettings(BaseModel):
    level: str = "INFO"


class KafkaSettings(BaseModel):
    bootstrap_servers: str = "kafka:29092"
    client_id: str = "analytics-service"
    group_id: str = "analytics-service"
    auto_offset_reset: str = "earliest"
    enable_auto_commit: bool = False


class AnalyticsTopicsSettings(BaseModel):
    order_events_topic: str = "order.analytics.events"
    payment_events_topic: str = "payment.analytics.events"


class RedisSettings(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ttl_seconds: int = 60
    key_prefix: str = "analytics"
    overview_key: str = "overview"

    @property
    def url(self) -> str:
        credentials = ""
        if self.password:
            credentials = f":{quote(self.password, safe='')}@"
        return f"redis://{credentials}{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    mongodb: MongoDBSettings
    api: ApiSettings
    kafka: KafkaSettings = KafkaSettings()
    analytics_topics: AnalyticsTopicsSettings = AnalyticsTopicsSettings()
    redis: RedisSettings = RedisSettings()
    logging: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_CONFIG__",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
