from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.DB_ECHO,
    connect_args={
        "ssl": "require" if settings.DB_SSLMODE == "require" else None,
        "server_settings": {"application_name": "tabi-formulario"},
    },
)

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
