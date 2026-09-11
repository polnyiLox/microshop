from pathlib import Path

from functools import lru_cache
from urllib.parse import quote

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).parent.parent.parent


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


class AuthJWTSettings(BaseModel):
    private_key_path: Path = BASE_DIR / "certs" / "jwt-private.pem"
    public_key_path: Path = BASE_DIR / "certs" / "jwt-public.pem"
    algorithm: str = "RS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7


class RefreshTokenCookiesSettings(BaseModel):
    key: str = "refresh_token"
    secure: bool = True
    httponly: bool = True
    same_site: str = "lax"


class InternalApiSettings(BaseModel):
    token: str = "change_me"


class RedisSettings(BaseModel):
    host: str = "redis"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ttl_seconds: int = 60
    key_prefix: str = "auth"
    balance_key: str = "balance:"

    @property
    def url(self) -> str:
        credentials = ""
        if self.password:
            credentials = f":{quote(self.password, safe='')}@"
        return f"redis://{credentials}{self.host}:{self.port}/{self.db}"


class Settings(BaseSettings):
    db: DataBaseSettings
    api: ApiSettings
    jwt_auth: AuthJWTSettings
    refresh_token_cookies: RefreshTokenCookiesSettings
    internal_api: InternalApiSettings = InternalApiSettings()
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
