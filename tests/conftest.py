from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.models import *  # noqa: F401, F403


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def _prepare_sqlite_schema() -> None:
    if test_engine.dialect.name != "sqlite":
        return
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if column.server_default is None:
                continue
            default_arg = getattr(column.server_default, "arg", "")
            if str(default_arg).upper().replace("()", "") in {"NOW", "CURRENT_TIMESTAMP"}:
                column.server_default = None


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database():
    from app.models.tabi import Rol

    _prepare_sqlite_schema()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        session.add(Rol(id=1, nombre="Propietario"))
        session.add(Rol(id=2, nombre="Administrador"))
        await session.commit()

    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.ping = AsyncMock(return_value=True)
    redis.pipeline = MagicMock(return_value=AsyncMock(
        __aenter__=AsyncMock(return_value=AsyncMock(
            incr=AsyncMock(),
            expire=AsyncMock(),
            execute=AsyncMock(return_value=[1, True]),
        )),
        __aexit__=AsyncMock(return_value=None),
        incr=AsyncMock(),
        expire=AsyncMock(),
        execute=AsyncMock(return_value=[1, True]),
    ))
    return redis


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, mock_redis) -> AsyncGenerator[AsyncClient, None]:
    from app.api.deps import get_db, get_redis_client
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data() -> dict[str, Any]:
    return {
        "email": "owner@testrestaurant.com",
        "password": "SecurePass123",
        "full_name": "Test Owner",
    }


@pytest.fixture
def admin_user_data() -> dict[str, Any]:
    return {
        "email": "admin@tabi.com",
        "password": "AdminPass123",
        "full_name": "Admin User",
    }


@pytest_asyncio.fixture
async def restaurant_id(client: AsyncClient) -> int:
    response = await client.post("/api/v1/onboarding/start")
    assert response.status_code == 201
    return response.json()["data"]["restaurant_id"]


@pytest_asyncio.fixture
async def onboarding_headers(restaurant_id: int) -> dict[str, str]:
    return {"X-Restaurant-Id": str(restaurant_id)}


@pytest_asyncio.fixture
async def registered_user(
    client: AsyncClient, test_user_data: dict, restaurant_id: int
) -> dict[str, Any]:
    payload = {**test_user_data, "restaurant_id": restaurant_id}
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(
    client: AsyncClient, test_user_data: dict, restaurant_id: int
) -> dict[str, str]:
    payload = {**test_user_data, "restaurant_id": restaurant_id}
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user_data["email"], "password": test_user_data["password"]},
    )
    tokens = resp.json()["data"]
    return {
        "Authorization": f"Bearer {tokens['access_token']}",
        "X-Restaurant-Id": str(restaurant_id),
    }


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession, admin_user_data: dict) -> dict[str, str]:
    from app.core.security import hash_password
    from app.models.tabi import Usuario
    from app.utils.names import split_full_name

    nombre, apellido = split_full_name(admin_user_data["full_name"])
    admin = Usuario(
        nombre=nombre,
        apellido=apellido or nombre,
        correo=admin_user_data["email"],
        contrasena=hash_password(admin_user_data["password"]),
        id_rol=2,
        activo=True,
    )
    db_session.add(admin)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": admin_user_data["email"], "password": admin_user_data["password"]},
    )
    tokens = resp.json()["data"]
    return {"Authorization": f"Bearer {tokens['access_token']}"}
