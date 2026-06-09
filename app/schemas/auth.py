from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.config import settings
from app.models.tabi import Usuario


def normalize_role(rol_nombre: str) -> str:
    lower = rol_nombre.lower()
    if lower in {settings.OWNER_ROLE_NAME.lower(), "propietario", "owner"}:
        return "owner"
    if lower in {settings.ADMIN_ROLE_NAME.lower(), "administrador", "admin"}:
        return "admin"
    return lower


@dataclass
class AuthUser:
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    restaurant_id: int | None

    @classmethod
    def from_usuario(cls, usuario: Usuario, rol_nombre: str) -> AuthUser:
        return cls(
            id=usuario.id,
            email=usuario.correo,
            full_name=f"{usuario.nombre} {usuario.apellido}".strip(),
            role=normalize_role(rol_nombre),
            is_active=bool(usuario.activo),
            is_verified=False,
            restaurant_id=usuario.id_restaurante,
        )


class RegisterRequest(BaseModel):
    restaurant_id: int = Field(gt=0, description="ID from POST /onboarding/start")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=255)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    restaurant_id: int | None

    @classmethod
    def from_usuario(cls, usuario: Usuario, rol_nombre: str) -> UserOut:
        auth = AuthUser.from_usuario(usuario, rol_nombre)
        return cls(
            id=auth.id,
            email=auth.email,
            full_name=auth.full_name,
            role=auth.role,
            is_active=auth.is_active,
            is_verified=auth.is_verified,
            restaurant_id=auth.restaurant_id,
        )
