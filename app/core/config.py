from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Tabi Formulario API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001

    # Database
    DB_HOST: str = "db.bakkcbqdcuktgmzztxcr.supabase.co"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "postgres"
    DB_SSLMODE: str = "require"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_TTL_ONBOARDING_STATUS: int = 60  # seconds

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Tabi roles
    OWNER_ROLE_ID: int | None = None
    OWNER_ROLE_NAME: str = "Propietario"
    ADMIN_ROLE_ID: int | None = None
    ADMIN_ROLE_NAME: str = "Administrador"

    # JWT
    SECRET_KEY: str = "super-secret-key-change-in-production-must-be-at-least-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS (comma-separated in .env, e.g. http://localhost:3000,http://localhost:5173)
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins(self) -> list[str]:
        value = self.CORS_ORIGINS.strip()
        if value.startswith("["):
            return json.loads(value)
        return [origin.strip() for origin in value.split(",") if origin.strip()]

    # Rate limiting
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_ONBOARDING: str = "60/minute"

    # File uploads
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_DOC_TYPES: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
    ]

    # Storage (Supabase Storage or S3 compatible)
    STORAGE_BUCKET: str = "restaurant-documents"
    STORAGE_URL: str = ""

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
