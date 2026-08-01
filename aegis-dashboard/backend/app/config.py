"""
Application Configuration
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Aegis Dashboard API"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://aegis:aegis@localhost:5432/aegis_dashboard"
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 50

    # Authentication
    secret_key: str = "dev-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # API Keys (for SDK ingestion)
    api_key_prefix: str = "ak_"

    # Rate Limiting
    rate_limit_per_minute: int = 100

    # Batch Writing
    batch_size: int = 100
    batch_timeout_seconds: int = 5

    # CORS
    cors_origins: list[str] = ["http://localhost:3003"]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
