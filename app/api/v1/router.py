from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.onboarding import router as onboarding_router
from app.api.v1.endpoints.uploads import router as uploads_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(onboarding_router)
api_router.include_router(uploads_router)
