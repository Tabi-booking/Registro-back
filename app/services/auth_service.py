from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.tabi import Usuario
from app.repositories.tabi_repository import RestauranteRepository, RolRepository, UsuarioRepository
from app.schemas.auth import AuthUser, TokenResponse, UserOut, normalize_role
from app.utils.names import split_full_name

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.usuario_repo = UsuarioRepository(session)
        self.rol_repo = RolRepository(session)
        self.restaurante_repo = RestauranteRepository(session)

    async def _resolve_owner_role_id(self) -> int:
        if settings.OWNER_ROLE_ID is not None:
            return settings.OWNER_ROLE_ID
        rol = await self.rol_repo.get_by_name(settings.OWNER_ROLE_NAME)
        if not rol:
            raise BadRequestError(
                f"Owner role '{settings.OWNER_ROLE_NAME}' not found. "
                "Set OWNER_ROLE_ID in environment."
            )
        return rol.id

    async def _resolve_role_name(self, usuario: Usuario) -> str:
        rol = await self.rol_repo.get(usuario.id_rol)
        return rol.nombre if rol else settings.OWNER_ROLE_NAME

    async def _build_auth_user(self, usuario: Usuario) -> AuthUser:
        rol_nombre = await self._resolve_role_name(usuario)
        return AuthUser.from_usuario(usuario, rol_nombre)

    async def register(
        self,
        restaurant_id: int,
        email: str,
        password: str,
        full_name: str,
        ip_address: str | None = None,
    ) -> UserOut:
        del ip_address

        restaurante = await self.restaurante_repo.get(restaurant_id)
        if not restaurante:
            raise NotFoundError("Restaurant", restaurant_id)

        if not await self.restaurante_repo.is_onboarding_started(restaurant_id):
            raise BadRequestError(
                "Restaurant onboarding not started. Call POST /api/v1/onboarding/start first."
            )

        owner_role_id = await self._resolve_owner_role_id()
        if await self.usuario_repo.get_owner_by_restaurant(restaurant_id, owner_role_id):
            raise ConflictError("This restaurant already has a registered owner")

        if await self.usuario_repo.get_by_email(email):
            raise ConflictError(f"Email '{email}' is already registered")

        hashed = hash_password(password)
        nombre, apellido = split_full_name(full_name)
        telefono = restaurante.telefono

        usuario = await self.usuario_repo.create(
            nombre=nombre,
            apellido=apellido or nombre,
            telefono=telefono,
            correo=email,
            contrasena=hashed,
            id_rol=owner_role_id,
            id_restaurante=restaurant_id,
            activo=True,
        )
        await self.session.commit()

        logger.info(
            "User registered for restaurant_id=%s: %s (id=%s)",
            restaurant_id,
            email,
            usuario.id,
        )
        rol_nombre = await self._resolve_role_name(usuario)
        return UserOut.from_usuario(usuario, rol_nombre)

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> TokenResponse:
        del ip_address

        usuario = await self.usuario_repo.get_by_email(email)
        if not usuario or not verify_password(password, usuario.contrasena):
            raise UnauthorizedError("Invalid email or password")

        if not usuario.activo:
            raise UnauthorizedError("Account is disabled")

        raw_refresh, hashed_refresh = create_refresh_token()
        await self.usuario_repo.update(usuario, refresh_token_hash=hashed_refresh)

        rol_nombre = await self._resolve_role_name(usuario)
        role = normalize_role(rol_nombre)
        extra_claims = {"role": role, "restaurant_id": usuario.id_restaurante}
        access_token = create_access_token(usuario.id, extra_claims=extra_claims)

        await self.session.commit()
        logger.info("User logged in: %s (id=%s)", email, usuario.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def refresh(self, raw_refresh_token: str) -> TokenResponse:

        token_hash = hash_token(raw_refresh_token)
        usuario = await self.usuario_repo.get_by_refresh_token_hash(token_hash)
        if not usuario:
            raise UnauthorizedError("Invalid or expired refresh token")

        if not usuario.activo:
            raise UnauthorizedError("Account is disabled")

        raw_refresh, hashed_refresh = create_refresh_token()
        rol_nombre = await self._resolve_role_name(usuario)
        role = normalize_role(rol_nombre)
        extra_claims = {"role": role, "restaurant_id": usuario.id_restaurante}
        access_token = create_access_token(usuario.id, extra_claims=extra_claims)

        await self.usuario_repo.update(usuario, refresh_token_hash=hashed_refresh)
        await self.session.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, raw_refresh_token: str) -> None:
        token_hash = hash_token(raw_refresh_token)
        usuario = await self.usuario_repo.get_by_refresh_token_hash(token_hash)
        if usuario:
            await self.usuario_repo.update(usuario, refresh_token_hash=None)
            await self.session.commit()
            logger.info("User logged out: id=%s", usuario.id)

    async def get_current_user(self, user_id: int) -> AuthUser | None:
        usuario = await self.usuario_repo.get(user_id)
        if not usuario:
            return None
        return await self._build_auth_user(usuario)
