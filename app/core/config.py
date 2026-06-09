from __future__ import annotations

import json
import os
from typing import Literal
from urllib.parse import quote_plus

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
    # Use Supabase pooler (port 6543) on serverless — avoids exhausting DB connections
    DB_USE_POOLER: bool = False

    @property
    def is_vercel(self) -> bool:
        return os.getenv("VERCEL") == "1"

    @property
    def is_serverless(self) -> bool:
        return self.is_vercel or self.DB_USE_POOLER

    @property
    def effective_db_pool_size(self) -> int:
        if self.is_serverless:
            return 1
        return self.DB_POOL_SIZE

    @property
    def effective_db_max_overflow(self) -> int:
        if self.is_serverless:
            return 0
        return self.DB_MAX_OVERFLOW

    @property
    def DATABASE_URL(self) -> str:
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        password = quote_plus(self.DB_PASSWORD)
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis — set REDIS_CONNECTION_URL (e.g. Upstash) on Vercel
    REDIS_CONNECTION_URL: str = ""
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_TTL_ONBOARDING_STATUS: int = 60  # seconds

    @property
    def REDIS_URL(self) -> str:
        explicit = self.REDIS_CONNECTION_URL.strip() or os.getenv("REDIS_URL", "").strip()
        if explicit:
            return explicit
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

    # CORS: "*" permite cualquier origen; o lista separada por comas / JSON array
    CORS_ORIGINS: str = "*"

    @property
    def cors_allow_all(self) -> bool:
        value = self.CORS_ORIGINS.strip().lower()
        return value in ("*", "all", "any")

    @property
    def cors_origins(self) -> list[str]:
        if self.cors_allow_all:
            return ["*"]
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
