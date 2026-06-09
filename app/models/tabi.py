from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, SmallInteger, String, Text, Time

BigIntPK = BigInteger().with_variant(Integer, "sqlite")
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Ubicacion(Base):
    __tablename__ = "ubicacion"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    pais: Mapped[str] = mapped_column(String, nullable=False)
    departamento: Mapped[str | None] = mapped_column(String, nullable=True)
    ciudad: Mapped[str] = mapped_column(String, nullable=False)
    barrio: Mapped[str | None] = mapped_column(String, nullable=True)
    id_ciudad: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Categoria(Base):
    __tablename__ = "categorias"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Etiqueta(Base):
    __tablename__ = "etiquetas"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    svg: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Restaurante(Base):
    __tablename__ = "restaurante"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    id_acceso: Mapped[str | None] = mapped_column(String, nullable=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    direccion: Mapped[str] = mapped_column(String, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    calificacion: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    horarios: Mapped[str | None] = mapped_column(String, nullable=True)
    imagen_destacada: Mapped[str | None] = mapped_column(String, nullable=True)
    google_maps: Mapped[str | None] = mapped_column(String, nullable=True)
    id_ubicacion: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    id_categoria: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    id_etiqueta: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    razon_social: Mapped[str | None] = mapped_column(String, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    sitio_web: Mapped[str | None] = mapped_column(String, nullable=True)
    redes_sociales: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    capacidad_asientos: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    numero_mesas: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    onboarding_paso: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, default=1)
    onboarding_estado: Mapped[str | None] = mapped_column(String, nullable=True, default="borrador")
    onboarding_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True, default=0)
    onboarding_datos: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    onboarding_enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Rol(Base):
    __tablename__ = "rol"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String, nullable=False)
    apellido: Mapped[str] = mapped_column(String, nullable=False)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    correo: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    contrasena: Mapped[str] = mapped_column(String, nullable=False)
    id_rol: Mapped[int] = mapped_column(BigInteger, nullable=False)
    id_restaurante: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refresh_token_hash: Mapped[str | None] = mapped_column(String, nullable=True)


class Horario(Base):
    __tablename__ = "horarios"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    id_restaurante: Mapped[int] = mapped_column(BigInteger, nullable=False)
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hora_apertura: Mapped[time] = mapped_column(Time, nullable=False)
    hora_cierre: Mapped[time] = mapped_column(Time, nullable=False)
    etiqueta_dia: Mapped[str | None] = mapped_column(String, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class RestauranteImagen(Base):
    __tablename__ = "restaurante_imagen"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    id_restaurante: Mapped[int] = mapped_column(BigInteger, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String, nullable=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    orden: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class DocumentoRestaurante(Base):
    __tablename__ = "documento_restaurante"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    id_restaurante: Mapped[int] = mapped_column(BigInteger, nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String, nullable=True)
    nombre_archivo: Mapped[str | None] = mapped_column(String, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamano_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class RestauranteEtiqueta(Base):
    __tablename__ = "restaurante_etiqueta"

    id_restaurante: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    id_etiqueta: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class RestauranteCategoria(Base):
    __tablename__ = "restaurante_categoria"

    id_restaurante: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    id_categoria: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class RestauranteTipoReserva(Base):
    __tablename__ = "restaurante_tipo_reserva"

    id_restaurante: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), primary_key=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class SuscripcionRestaurante(Base):
    __tablename__ = "suscripcion_restaurante"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    id_restaurante: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")
    ciclo_facturacion: Mapped[str] = mapped_column(String(20), nullable=False, default="monthly")
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="trial")
    inicio_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expira_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
