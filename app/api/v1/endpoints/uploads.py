from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import DBSession, OnboardingSession
from app.schemas.common import APIResponse
from app.schemas.onboarding import (
    ConfirmUploadRequest,
    PresignedUrlRequest,
    PresignedUrlResponse,
)
from app.services.upload_service import UploadService

router = APIRouter(prefix="/uploads", tags=["Uploads"])


def _ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/presigned", response_model=APIResponse[PresignedUrlResponse])
async def get_presigned_url(
    body: PresignedUrlRequest,
    db: DBSession,
    session: OnboardingSession,
) -> APIResponse[PresignedUrlResponse]:
    service = UploadService(db)
    result = await service.get_presigned_url(
        request=body,
        restaurant_id=session.restaurant_id,
        user_id=session.user_id or 0,
    )
    return APIResponse(data=result, message="Presigned URL generated")


@router.post("/confirm", response_model=APIResponse[dict])
async def confirm_upload(
    body: ConfirmUploadRequest,
    request: Request,
    db: DBSession,
    session: OnboardingSession,
) -> APIResponse[dict]:
    service = UploadService(db)
    result = await service.confirm_upload(
        request=body,
        restaurant_id=session.restaurant_id,
        user_id=session.user_id or 0,
        ip_address=_ip(request),
    )
    return APIResponse(data=result, message="Upload confirmed")
