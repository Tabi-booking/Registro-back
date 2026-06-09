from __future__ import annotations

import pytest
from httpx import AsyncClient

STEP1_DATA = {
    "restaurant_name": "La Trattoria",
    "legal_name": "La Trattoria SAS",
    "restaurant_type": "casual",
    "description": "A cozy Italian restaurant in the heart of the city.",
    "website": "https://latrattoria.co",
    "social_links": {"instagram": "https://instagram.com/latrattoria"},
}

STEP2_DATA = {
    "country": "Colombia",
    "city": "Bogota",
    "address": "Calle 93 #11-27, Zona Rosa",
    "lat": 4.676,
    "lng": -74.048,
}

STEP3_DATA = {
    "owner_name": "Carlos Perez",
    "email": "carlos@latrattoria.co",
    "phone": "+573001234567",
}

STEP4_DATA = {
    "opening_hours": "08:00:00",
    "closing_hours": "22:00:00",
    "seating_capacity": 80,
    "number_tables": 20,
}

STEP5_DATA = {
    "reservation_types": ["online", "phone"],
    "cuisine_types": ["italian", "pasta"],
    "services_offered": ["wifi", "parking"],
}

STEP6_DATA = {
    "logo_key": None,
    "cover_image_keys": [],
    "document_keys": [],
}

STEP7_DATA = {
    "plan": "pro",
    "billing_cycle": "monthly",
}


@pytest.mark.asyncio
class TestOnboardingStart:
    async def test_start_onboarding(self, client: AsyncClient):
        response = await client.post("/api/v1/onboarding/start")
        assert response.status_code == 201
        body = response.json()
        assert body["success"] is True
        assert "restaurant_id" in body["data"]

    async def test_start_is_public(self, client: AsyncClient):
        response = await client.post("/api/v1/onboarding/start")
        assert response.status_code == 201


@pytest.mark.asyncio
class TestOnboardingSteps:
    async def test_save_step1_valid(self, client: AsyncClient, onboarding_headers: dict):
        response = await client.post(
            "/api/v1/onboarding/step/1", json=STEP1_DATA, headers=onboarding_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["step"] == 1
        assert 1 in body["data"]["steps_completed"]

    async def test_save_step1_invalid_missing_fields(
        self, client: AsyncClient, onboarding_headers: dict
    ):
        response = await client.post(
            "/api/v1/onboarding/step/1",
            json={"restaurant_name": "Too short"},
            headers=onboarding_headers,
        )
        assert response.status_code == 422

    async def test_save_step1_name_too_short(self, client: AsyncClient, onboarding_headers: dict):
        bad_data = {**STEP1_DATA, "restaurant_name": "AB"}
        response = await client.post(
            "/api/v1/onboarding/step/1", json=bad_data, headers=onboarding_headers
        )
        assert response.status_code == 422

    async def test_patch_step_updates_data(self, client: AsyncClient, onboarding_headers: dict):
        await client.post(
            "/api/v1/onboarding/step/1", json=STEP1_DATA, headers=onboarding_headers
        )
        updated = {**STEP1_DATA, "description": "Updated description for the restaurant."}
        response = await client.patch(
            "/api/v1/onboarding/step/1", json=updated, headers=onboarding_headers
        )
        assert response.status_code == 200

    async def test_invalid_step_number(self, client: AsyncClient, onboarding_headers: dict):
        response = await client.post(
            "/api/v1/onboarding/step/99", json={}, headers=onboarding_headers
        )
        assert response.status_code in (400, 422)


@pytest.mark.asyncio
class TestOnboardingStatus:
    async def test_get_status_after_step1(self, client: AsyncClient, onboarding_headers: dict):
        await client.post(
            "/api/v1/onboarding/step/1", json=STEP1_DATA, headers=onboarding_headers
        )

        response = await client.get("/api/v1/onboarding/status", headers=onboarding_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["data"]["completion_percentage"] > 0
        assert 1 in body["data"]["steps_completed"]

    async def test_status_requires_restaurant_header(self, client: AsyncClient):
        response = await client.get("/api/v1/onboarding/status")
        assert response.status_code == 400


@pytest.mark.asyncio
class TestOnboardingSubmit:
    async def test_submit_incomplete_fails(self, client: AsyncClient, auth_headers: dict):
        await client.post(
            "/api/v1/onboarding/step/1", json=STEP1_DATA, headers=auth_headers
        )

        response = await client.post("/api/v1/onboarding/submit", headers=auth_headers)
        assert response.status_code == 400
        assert "Required steps not completed" in response.json()["error"]

    async def test_full_flow_submit_success(self, client: AsyncClient, auth_headers: dict):
        for step_num, data in [
            (1, STEP1_DATA),
            (2, STEP2_DATA),
            (3, STEP3_DATA),
            (4, STEP4_DATA),
            (5, STEP5_DATA),
            (6, STEP6_DATA),
            (7, STEP7_DATA),
        ]:
            r = await client.post(
                f"/api/v1/onboarding/step/{step_num}", json=data, headers=auth_headers
            )
            assert r.status_code == 200, f"Step {step_num} failed: {r.text}"

        response = await client.post("/api/v1/onboarding/submit", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "submitted"

    async def test_double_submit_fails(self, client: AsyncClient, auth_headers: dict):
        for step_num, data in [(1, STEP1_DATA), (2, STEP2_DATA), (3, STEP3_DATA)]:
            await client.post(
                f"/api/v1/onboarding/step/{step_num}", json=data, headers=auth_headers
            )

        await client.post("/api/v1/onboarding/submit", headers=auth_headers)
        response = await client.post("/api/v1/onboarding/submit", headers=auth_headers)
        assert response.status_code == 400
