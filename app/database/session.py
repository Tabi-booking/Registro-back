from __future__ import annotations

import logging
import os
import socket
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
redis_client: aioredis.Redis | None = None


def _has_explicit_database_url() -> bool:
    return bool(settings.DATABASE_URL.strip() or os.getenv("DATABASE_URL", "").strip())


def _resolve_db_host(host: str) -> str:
    """Prefer IPv4 on serverless — Supabase direct hostnames are often IPv6-only."""
    if not settings.is_serverless:
        return host
    try:
        infos = socket.getaddrinfo(host, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except OSError:
        pass
    return host


def _database_url() -> str:
    url = settings.async_database_url
    if settings.is_serverless and settings.uses_direct_supabase_host and not _has_explicit_database_url():
        logger.warning(
            "DB_HOST uses direct Supabase hostname on serverless. "
            "Use the connection pooler (port 6543) or set DATABASE_URL in Vercel."
        )
    if not _has_explicit_database_url() and settings.DB_HOST:
        host = _resolve_db_host(settings.DB_HOST)
        if host != settings.DB_HOST:
            url = url.replace(f"@{settings.DB_HOST}:", f"@{host}:")
    return url


def _connect_args() -> dict:
    args: dict = {
        "server_settings": {"application_name": "tabi-formulario"},
    }
    if settings.DB_SSLMODE == "require":
        args["ssl"] = "require"
    if settings.is_serverless:
        args["statement_cache_size"] = 0
        args["prepared_statement_cache_size"] = 0
    return args


def _create_engine() -> AsyncEngine:
    url = _database_url()
    if settings.is_serverless:
        logger.info(
            "Creating serverless DB engine (NullPool) url_host=%s port=%s user=%s",
            settings.DB_HOST,
            settings.effective_db_port,
            settings.effective_db_user,
        )
        return create_async_engine(
            url,
            poolclass=NullPool,
            echo=settings.DB_ECHO,
            connect_args=_connect_args(),
        )
    return create_async_engine(
        url,
        pool_size=settings.effective_db_pool_size,
        max_overflow=settings.effective_db_max_overflow,
        echo=settings.DB_ECHO,
        connect_args=_connect_args(),
    )


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


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
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
