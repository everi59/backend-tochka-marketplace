from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env.docker"),
        case_sensitive=True,
        extra="ignore"
    )


class DatabaseConfig(Config):
    """Настройки базы данных"""
    DB_NAME: str = Field(default="marketplace_db")
    DB_USER: str = Field(default="postgres")
    DB_PASS: str = Field(default="postgres")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: str = Field(default="5432")

    DB_POOL_SIZE: int = Field(default=20)
    DB_MAX_OVERFLOW: int = Field(default=40)
    DB_POOL_TIMEOUT: int = Field(default=30)
    DB_POOL_RECYCLE: int = Field(default=3600)

    def get_url(self, is_async: bool = True) -> str:
        driver = "postgresql+asyncpg" if is_async else "postgresql"
        return f"{driver}://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


class AppConfig(Config):
    """Настройки приложения"""
    APP_NAME: str = Field(default="Marketplace API")
    APP_VERSION: str = Field(default="1.0.0")
    DEBUG: bool = Field(default=True)
    LOG_LEVEL: str = Field(default="DEBUG")
    STATIC_DIR: str = Field(default="/app/static")
    IMAGES_DIR: str = Field(default="/app/static/images/products")

    # API documentation
    DOCS_URL: str = Field(default="/docs")
    REDOC_URL: str = Field(default="/redoc")
    OPENAPI_URL: str = Field(default="/openapi.json")

    # Server
    API_PREFIX: str = Field(default="/api/v1")
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # CORS
    CORS_ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:5173")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)

    # Internal service auth
    B2B_SERVICE_KEY: str = Field(default="svc")

    def get_cors_origins(self) -> List[str]:
        origins = [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
        if self.DEBUG and "*" not in origins:
            origins.append("http://localhost:*")
            origins.append("http://127.0.0.1:*")
        return origins


class Settings(Config):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    app: AppConfig = Field(default_factory=AppConfig)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
DB_CONFIG = settings.database
APP_CONFIG = settings.app
