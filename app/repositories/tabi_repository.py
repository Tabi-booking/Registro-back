from __future__ import annotations

from datetime import datetime, time, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tabi import (
    Categoria,
    DocumentoRestaurante,
    Etiqueta,
    Horario,
    Restaurante,
    RestauranteCategoria,
    RestauranteEtiqueta,
    RestauranteImagen,
    RestauranteTipoReserva,
    Rol,
    SuscripcionRestaurante,
    Ubicacion,
    Usuario,
)
from app.repositories.base import BaseRepository


class UbicacionRepository(BaseRepository[Ubicacion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Ubicacion, session)


class CategoriaRepository(BaseRepository[Categoria]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Categoria, session)

    async def get_or_create(self, nombre: str) -> Categoria:
        existing = await self.get_by(nombre=nombre)
        if existing:
            return existing
        return await self.create(nombre=nombre)


class EtiquetaRepository(BaseRepository[Etiqueta]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Etiqueta, session)

    async def get_or_create(self, nombre: str) -> Etiqueta:
        existing = await self.get_by(nombre=nombre)
        if existing:
            return existing
        return await self.create(nombre=nombre)


class RestauranteRepository(BaseRepository[Restaurante]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Restaurante, session)

    async def create_stub(self) -> Restaurante:
        now = datetime.now(timezone.utc)
        return await self.create(
            nombre="Borrador",
            direccion="Pendiente",
            activo=False,
            onboarding_paso=1,
            onboarding_estado="borrador",
            onboarding_pct=0,
            onboarding_datos={},
            created_at=now,
            updated_at=now,
        )

    async def is_onboarding_started(self, restaurant_id: int) -> bool:
        restaurante = await self.get(restaurant_id)
        return restaurante is not None and restaurante.onboarding_estado is not None


class RolRepository(BaseRepository[Rol]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Rol, session)

    async def get_by_name(self, nombre: str) -> Rol | None:
        return await self.get_by(nombre=nombre)


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Usuario, session)

    async def get_by_email(self, correo: str) -> Usuario | None:
        return await self.get_by(correo=correo)

    async def get_by_refresh_token_hash(self, token_hash: str) -> Usuario | None:
        return await self.get_by(refresh_token_hash=token_hash)

    async def get_owner_by_restaurant(
        self, restaurant_id: int, owner_role_id: int
    ) -> Usuario | None:
        stmt = select(Usuario).where(
            Usuario.id_restaurante == restaurant_id,
            Usuario.id_rol == owner_role_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class HorarioRepository(BaseRepository[Horario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Horario, session)

    async def replace_weekly_schedule(
        self,
        restaurant_id: int,
        opening: time,
        closing: time,
    ) -> list[Horario]:
        await self.session.execute(
            delete(Horario).where(Horario.id_restaurante == restaurant_id)
        )
        rows: list[Horario] = []
        for day in range(7):
            row = Horario(
                id_restaurante=restaurant_id,
                dia_semana=day,
                hora_apertura=opening,
                hora_cierre=closing,
                activo=True,
            )
            self.session.add(row)
            rows.append(row)
        await self.session.flush()
        return rows


class RestauranteImagenRepository(BaseRepository[RestauranteImagen]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RestauranteImagen, session)

    async def list_by_restaurant(self, restaurant_id: int) -> list[RestauranteImagen]:
        stmt = (
            select(RestauranteImagen)
            .where(RestauranteImagen.id_restaurante == restaurant_id)
            .order_by(RestauranteImagen.orden)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def replace_covers(
        self, restaurant_id: int, items: list[dict[str, str | int | None]]
    ) -> list[RestauranteImagen]:
        await self.session.execute(
            delete(RestauranteImagen).where(RestauranteImagen.id_restaurante == restaurant_id)
        )
        rows: list[RestauranteImagen] = []
        for idx, item in enumerate(items):
            row = RestauranteImagen(
                id_restaurante=restaurant_id,
                url=str(item["url"]),
                storage_key=item.get("storage_key"),
                es_principal=False,
                orden=idx + 1,
            )
            self.session.add(row)
            rows.append(row)
        await self.session.flush()
        return rows

    async def upsert_by_storage_key(
        self,
        restaurant_id: int,
        url: str,
        storage_key: str,
        orden: int | None = None,
    ) -> RestauranteImagen:
        existing = await self.get_by(storage_key=storage_key)
        if existing:
            return await self.update(existing, url=url, orden=orden or existing.orden)
        if orden is None:
            images = await self.list_by_restaurant(restaurant_id)
            orden = len(images) + 1
        return await self.create(
            id_restaurante=restaurant_id,
            url=url,
            storage_key=storage_key,
            es_principal=False,
            orden=orden,
        )


class DocumentoRestauranteRepository(BaseRepository[DocumentoRestaurante]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DocumentoRestaurante, session)

    async def get_by_storage_key(self, storage_key: str) -> DocumentoRestaurante | None:
        return await self.get_by(storage_key=storage_key)

    async def list_by_restaurant(self, restaurant_id: int) -> list[DocumentoRestaurante]:
        stmt = select(DocumentoRestaurante).where(
            DocumentoRestaurante.id_restaurante == restaurant_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_storage_keys(
        self, restaurant_id: int, storage_keys: list[str]
    ) -> list[DocumentoRestaurante]:
        if not storage_keys:
            return []
        stmt = select(DocumentoRestaurante).where(
            DocumentoRestaurante.id_restaurante == restaurant_id,
            DocumentoRestaurante.storage_key.in_(storage_keys),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class RestauranteEtiquetaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_restaurant(
        self, restaurant_id: int, etiqueta_ids: list[int]
    ) -> None:
        await self.session.execute(
            delete(RestauranteEtiqueta).where(
                RestauranteEtiqueta.id_restaurante == restaurant_id
            )
        )
        for etiqueta_id in etiqueta_ids:
            self.session.add(
                RestauranteEtiqueta(id_restaurante=restaurant_id, id_etiqueta=etiqueta_id)
            )
        await self.session.flush()


class RestauranteCategoriaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_restaurant(
        self, restaurant_id: int, categoria_ids: list[int]
    ) -> None:
        await self.session.execute(
            delete(RestauranteCategoria).where(
                RestauranteCategoria.id_restaurante == restaurant_id
            )
        )
        for categoria_id in categoria_ids:
            self.session.add(
                RestauranteCategoria(
                    id_restaurante=restaurant_id, id_categoria=categoria_id
                )
            )
        await self.session.flush()


class RestauranteTipoReservaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def replace_for_restaurant(self, restaurant_id: int, tipos: list[str]) -> None:
        await self.session.execute(
            delete(RestauranteTipoReserva).where(
                RestauranteTipoReserva.id_restaurante == restaurant_id
            )
        )
        for tipo in tipos:
            self.session.add(
                RestauranteTipoReserva(id_restaurante=restaurant_id, tipo=tipo)
            )
        await self.session.flush()


class SuscripcionRestauranteRepository(BaseRepository[SuscripcionRestaurante]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SuscripcionRestaurante, session)

    async def upsert(
        self,
        restaurant_id: int,
        plan: str,
        ciclo_facturacion: str,
        estado: str = "trial",
    ) -> SuscripcionRestaurante:
        existing = await self.get_by(id_restaurante=restaurant_id)
        now = datetime.now(timezone.utc)
        if existing:
            return await self.update(
                existing,
                plan=plan,
                ciclo_facturacion=ciclo_facturacion,
                estado=estado,
                actualizado_en=now,
            )
        return await self.create(
            id_restaurante=restaurant_id,
            plan=plan,
            ciclo_facturacion=ciclo_facturacion,
            estado=estado,
            inicio_en=now,
            creado_en=now,
            actualizado_en=now,
        )
