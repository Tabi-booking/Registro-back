from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DBSession
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", response_model=APIResponse[UserOut], status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    db: DBSession,
) -> APIResponse[UserOut]:
    service = AuthService(db)
    user = await service.register(
        restaurant_id=body.restaurant_id,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        ip_address=_ip(request),
    )
    return APIResponse(data=user, message="Registration successful. Please verify your email.")


@router.post("/login", response_model=APIResponse[TokenResponse])
async def login(
    body: LoginRequest,
    request: Request,
    db: DBSession,
) -> APIResponse[TokenResponse]:
    service = AuthService(db)
    tokens = await service.login(
        email=body.email,
        password=body.password,
        ip_address=_ip(request),
    )
    return APIResponse(data=tokens, message="Login successful")


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_token(
    body: RefreshRequest,
    db: DBSession,
) -> APIResponse[TokenResponse]:
    service = AuthService(db)
    tokens = await service.refresh(body.refresh_token)
    return APIResponse(data=tokens, message="Token refreshed")


@router.post("/logout", response_model=APIResponse[None])
async def logout(
    body: LogoutRequest,
    db: DBSession,
) -> APIResponse[None]:
    service = AuthService(db)
    await service.logout(body.refresh_token)
    return APIResponse(data=None, message="Logged out successfully")


@router.get("/me", response_model=APIResponse[UserOut])
async def me(current_user: CurrentUser) -> APIResponse[UserOut]:
    return APIResponse(
        data=UserOut(
            id=current_user.id,
            email=current_user.email,
            full_name=current_user.full_name,
            role=current_user.role,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            restaurant_id=current_user.restaurant_id,
        ),
        message="OK",
    )
