from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRegister:
    async def test_register_success(
        self, client: AsyncClient, test_user_data: dict, restaurant_id: int
    ):
        payload = {**test_user_data, "restaurant_id": restaurant_id}
        response = await client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert body["data"]["email"] == test_user_data["email"]
        assert body["data"]["restaurant_id"] == restaurant_id
        assert "hashed_password" not in body["data"]

    async def test_register_duplicate_email(
        self, client: AsyncClient, test_user_data: dict, restaurant_id: int
    ):
        payload = {**test_user_data, "restaurant_id": restaurant_id}
        await client.post("/api/v1/auth/register", json=payload)
        start = await client.post("/api/v1/onboarding/start")
        other_restaurant_id = start.json()["data"]["restaurant_id"]
        duplicate = {**test_user_data, "restaurant_id": other_restaurant_id}
        response = await client.post("/api/v1/auth/register", json=duplicate)
        assert response.status_code == 409
        assert response.json()["success"] is False
        assert response.json()["code"] == "CONFLICT"

    async def test_register_weak_password(self, client: AsyncClient, restaurant_id: int):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "restaurant_id": restaurant_id,
                "email": "weak@example.com",
                "password": "weak",
                "full_name": "Test",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_email(self, client: AsyncClient, restaurant_id: int):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "restaurant_id": restaurant_id,
                "email": "not-an-email",
                "password": "SecurePass123",
                "full_name": "Test",
            },
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestLogin:
    async def test_login_success(
        self, client: AsyncClient, test_user_data: dict, restaurant_id: int
    ):
        await client.post(
            "/api/v1/auth/register",
            json={**test_user_data, "restaurant_id": restaurant_id},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"

    async def test_login_wrong_password(
        self, client: AsyncClient, test_user_data: dict, restaurant_id: int
    ):
        await client.post(
            "/api/v1/auth/register",
            json={**test_user_data, "restaurant_id": restaurant_id},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": "WrongPassword1"},
        )
        assert response.status_code == 401
        assert response.json()["code"] == "UNAUTHORIZED"

    async def test_login_nonexistent_user(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "SomePass123"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
class TestRefreshLogout:
    async def test_refresh_token(
        self, client: AsyncClient, test_user_data: dict, restaurant_id: int
    ):
        await client.post(
            "/api/v1/auth/register",
            json={**test_user_data, "restaurant_id": restaurant_id},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        refresh_token = login_resp.json()["data"]["refresh_token"]

        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body["data"]

    async def test_logout(
        self, client: AsyncClient, test_user_data: dict, restaurant_id: int
    ):
        await client.post(
            "/api/v1/auth/register",
            json={**test_user_data, "restaurant_id": restaurant_id},
        )
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": test_user_data["email"], "password": test_user_data["password"]},
        )
        refresh_token = login_resp.json()["data"]["refresh_token"]

        response = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Refresh should now fail
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 401

    async def test_me_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_me_returns_user(self, client: AsyncClient, auth_headers: dict):
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert "email" in response.json()["data"]
