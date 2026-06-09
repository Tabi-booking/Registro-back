from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _connect_args() -> dict:
    args: dict = {
        "server_settings": {"application_name": "tabi-formulario"},
    }
    if settings.DB_SSLMODE == "require":
        args["ssl"] = "require"
    if settings.is_serverless:
        # Required for Supabase pooler (PgBouncer transaction mode) + asyncpg
        args["statement_cache_size"] = 0
        args["prepared_statement_cache_size"] = 0
    return args


def _create_engine():
    if settings.is_serverless:
        return create_async_engine(
            settings.DATABASE_URL,
            poolclass=NullPool,
            echo=settings.DB_ECHO,
            connect_args=_connect_args(),
        )
    return create_async_engine(
        settings.DATABASE_URL,
        pool_size=settings.effective_db_pool_size,
        max_overflow=settings.effective_db_max_overflow,
        echo=settings.DB_ECHO,
        connect_args=_connect_args(),
    )


engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

redis_client: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
