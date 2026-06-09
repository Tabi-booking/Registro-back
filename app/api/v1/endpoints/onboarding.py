from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.api.deps import CurrentAdmin, CurrentUser, DBSession, OnboardingSession, RedisClient
from app.core.exceptions import BadRequestError
from app.schemas.common import APIResponse
from app.schemas.onboarding import OnboardingStartResponse, OnboardingStatusResponse
from app.schemas.restaurant import FullOnboardingDataResponse
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])


def _ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/start", response_model=APIResponse[OnboardingStartResponse], status_code=201)
async def start_onboarding(
    request: Request,
    db: DBSession,
    redis: RedisClient,
) -> APIResponse[OnboardingStartResponse]:
    """Public endpoint — creates restaurant first, before user registration."""
    service = OnboardingService(db, redis)
    result = await service.start_onboarding(ip_address=_ip(request))
    return APIResponse(
        data=OnboardingStartResponse(**result),
        message=result["message"],
    )


@router.post("/step/{step_number}", response_model=APIResponse[dict])
async def save_step(
    step_number: int,
    body: dict,
    request: Request,
    db: DBSession,
    redis: RedisClient,
    session: OnboardingSession,
) -> APIResponse[dict]:
    service = OnboardingService(db, redis)
    result = await service.save_step(
        restaurant_id=session.restaurant_id,
        step_number=step_number,
        raw_data=body,
        user_id=session.user_id,
        ip_address=_ip(request),
    )
    return APIResponse(data=result, message=f"Step {step_number} saved")


@router.patch("/step/{step_number}", response_model=APIResponse[dict])
async def update_step(
    step_number: int,
    body: dict,
    request: Request,
    db: DBSession,
    redis: RedisClient,
    session: OnboardingSession,
) -> APIResponse[dict]:
    """Update (partial re-save) a step. Uses same logic as POST save."""
    service = OnboardingService(db, redis)
    result = await service.save_step(
        restaurant_id=session.restaurant_id,
        step_number=step_number,
        raw_data=body,
        user_id=session.user_id,
        ip_address=_ip(request),
    )
    return APIResponse(data=result, message=f"Step {step_number} updated")


@router.get("/status", response_model=APIResponse[OnboardingStatusResponse])
async def get_status(
    db: DBSession,
    redis: RedisClient,
    session: OnboardingSession,
) -> APIResponse[OnboardingStatusResponse]:
    service = OnboardingService(db, redis)
    status = await service.get_status(session.restaurant_id)
    return APIResponse(data=status, message="OK")


@router.post("/submit", response_model=APIResponse[dict])
async def submit_onboarding(
    request: Request,
    db: DBSession,
    redis: RedisClient,
    current_user: CurrentUser,
) -> APIResponse[dict]:
    """Requires authentication — user must register before final submit."""
    if not current_user.restaurant_id:
        raise BadRequestError("User is not linked to a restaurant")

    service = OnboardingService(db, redis)
    result = await service.submit_onboarding(
        restaurant_id=current_user.restaurant_id,
        user_id=current_user.id,
        ip_address=_ip(request),
    )
    return APIResponse(data=result, message=result["message"])


@router.get("/{restaurant_id}", response_model=APIResponse[FullOnboardingDataResponse])
async def get_full_onboarding(
    restaurant_id: int,
    db: DBSession,
    redis: RedisClient,
    current_user: CurrentAdmin,
) -> APIResponse[FullOnboardingDataResponse]:
    service = OnboardingService(db, redis)
    data = await service.get_full_data(restaurant_id)
    return APIResponse(data=data, message="OK")
