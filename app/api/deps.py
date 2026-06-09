from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.session import get_db, get_redis
from app.repositories.tabi_repository import RestauranteRepository, RolRepository, UsuarioRepository
from app.schemas.auth import AuthUser

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class OnboardingContext:
    restaurant_id: int
    user_id: int | None = None


async def get_redis_client() -> aioredis.Redis:
    return get_redis()


async def _get_user_from_token(
    credentials: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
) -> AuthUser | None:
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
        role = payload.get("role", "owner")
    except (JWTError, KeyError, ValueError):
        return None

    usuario_repo = UsuarioRepository(db)
    usuario = await usuario_repo.get(user_id)
    if not usuario or not usuario.activo:
        return None

    rol_repo = RolRepository(db)
    rol = await rol_repo.get(usuario.id_rol)
    rol_nombre = rol.nombre if rol else role
    return AuthUser.from_usuario(usuario, rol_nombre)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    user = await _get_user_from_token(credentials, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"success": False, "error": "Authentication required", "code": "UNAUTHORIZED"},
        )
    return user


async def get_onboarding_context(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)] = None,
    db: AsyncSession = Depends(get_db),
) -> OnboardingContext:
    user = await _get_user_from_token(credentials, db)
    if user and user.restaurant_id:
        return OnboardingContext(restaurant_id=user.restaurant_id, user_id=user.id)

    header = request.headers.get("X-Restaurant-Id")
    if not header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "X-Restaurant-Id header required before user registration",
                "code": "BAD_REQUEST",
            },
        )

    try:
        restaurant_id = int(header)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "error": "Invalid X-Restaurant-Id header",
                "code": "BAD_REQUEST",
            },
        )

    restaurante_repo = RestauranteRepository(db)
    if not await restaurante_repo.is_onboarding_started(restaurant_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "error": f"Onboarding session for restaurant '{restaurant_id}' not found",
                "code": "NOT_FOUND",
            },
        )

    return OnboardingContext(restaurant_id=restaurant_id, user_id=user.id if user else None)


async def get_current_admin(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
) -> AuthUser:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "error": "Admin access required", "code": "FORBIDDEN"},
        )
    return current_user


def require_own_restaurant(restaurant_id: int):
    async def _check(
        current_user: Annotated[AuthUser, Depends(get_current_user)],
    ) -> AuthUser:
        if current_user.role == "admin":
            return current_user
        if current_user.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "error": "Access denied to this restaurant",
                    "code": "FORBIDDEN",
                },
            )
        return current_user

    return _check


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
OnboardingSession = Annotated[OnboardingContext, Depends(get_onboarding_context)]
CurrentAdmin = Annotated[AuthUser, Depends(get_current_admin)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[aioredis.Redis, Depends(get_redis_client)]
