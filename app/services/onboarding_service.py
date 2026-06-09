from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.repositories.tabi_repository import (
    CategoriaRepository,
    DocumentoRestauranteRepository,
    EtiquetaRepository,
    HorarioRepository,
    RestauranteCategoriaRepository,
    RestauranteEtiquetaRepository,
    RestauranteImagenRepository,
    RestauranteRepository,
    RestauranteTipoReservaRepository,
    SuscripcionRestauranteRepository,
    UbicacionRepository,
)
from app.schemas.onboarding import (
    STEP_SCHEMA_MAP,
    OnboardingStatusResponse,
    Step1BasicInfo,
    Step2Location,
    Step3Contact,
    Step4Operations,
    Step5Features,
    Step6Files,
    Step7Plan,
)
from app.schemas.restaurant import (
    FullOnboardingDataResponse,
    RestaurantContactOut,
    RestaurantDocumentOut,
    RestaurantFeatureOut,
    RestaurantImageOut,
    RestaurantProfileOut,
    RestaurantSubscriptionOut,
)
from app.utils.sanitizers import sanitize_dict

logger = logging.getLogger(__name__)

ONBOARDING_ESTADO_BORRADOR = "borrador"
ONBOARDING_ESTADO_ENVIADO = "enviado"

API_STATUS_DRAFT = "draft"
API_STATUS_SUBMITTED = "submitted"

REQUIRED_STEPS = {1, 2, 3}
OPTIONAL_STEPS = {4, 5, 6, 7}
REQUIRED_WEIGHT = 60.0
OPTIONAL_WEIGHT = 40.0

RESTAURANT_TYPE_LABELS = {
    "casual": "Casual",
    "fine_dining": "Fine Dining",
    "fast_casual": "Fast Casual",
    "cafe": "Café",
    "bar": "Bar",
    "food_truck": "Food Truck",
    "other": "Otro",
}

SERVICE_LABELS = {
    "parking": "Parqueadero",
    "wifi": "WiFi",
    "terrace": "Terraza",
    "private_room": "Salón privado",
    "accessibility": "Accesibilidad",
    "live_music": "Música en vivo",
    "catering": "Catering",
    "delivery": "Domicilios",
    "takeaway": "Para llevar",
}


def _cache_key(restaurant_id: int) -> str:
    return f"onboarding:status:{restaurant_id}"


async def _redis_delete(redis: aioredis.Redis, key: str) -> None:
    try:
        await redis.delete(key)
    except Exception:
        logger.warning("Redis unavailable — cache delete skipped for %s", key)


async def _redis_get(redis: aioredis.Redis, key: str) -> str | None:
    try:
        return await redis.get(key)
    except Exception:
        logger.warning("Redis unavailable — cache read skipped for %s", key)
        return None


async def _redis_setex(redis: aioredis.Redis, key: str, ttl: int, value: str) -> None:
    try:
        await redis.setex(key, ttl, value)
    except Exception:
        logger.warning("Redis unavailable — cache write skipped for %s", key)


def _api_status(db_estado: str | None) -> str:
    if db_estado == ONBOARDING_ESTADO_ENVIADO:
        return API_STATUS_SUBMITTED
    return API_STATUS_DRAFT


def _steps_completed(onboarding_datos: dict | None) -> list[int]:
    if not onboarding_datos:
        return []
    completed: list[int] = []
    for key in onboarding_datos:
        if key.startswith("paso_"):
            try:
                completed.append(int(key.split("_", 1)[1]))
            except ValueError:
                continue
    return sorted(completed)


def _merge_step_data(existing: dict | None, step_number: int, data: dict) -> dict:
    merged = dict(existing or {})
    merged[f"paso_{step_number}"] = data
    return merged


class OnboardingService:
    def __init__(self, session: AsyncSession, redis: aioredis.Redis) -> None:
        self.session = session
        self.redis = redis
        self.restaurante_repo = RestauranteRepository(session)
        self.ubicacion_repo = UbicacionRepository(session)
        self.horario_repo = HorarioRepository(session)
        self.categoria_repo = CategoriaRepository(session)
        self.etiqueta_repo = EtiquetaRepository(session)
        self.restaurante_categoria_repo = RestauranteCategoriaRepository(session)
        self.restaurante_etiqueta_repo = RestauranteEtiquetaRepository(session)
        self.restaurante_tipo_reserva_repo = RestauranteTipoReservaRepository(session)
        self.imagen_repo = RestauranteImagenRepository(session)
        self.documento_repo = DocumentoRestauranteRepository(session)
        self.suscripcion_repo = SuscripcionRestauranteRepository(session)

    async def start_onboarding(self, ip_address: str | None = None) -> dict[str, Any]:
        restaurante = await self.restaurante_repo.create_stub()
        await self.session.commit()

        logger.info("Onboarding started for restaurant_id=%s", restaurante.id)
        return {"restaurant_id": restaurante.id, "message": "Onboarding started"}

    async def save_step(
        self,
        restaurant_id: int,
        step_number: int,
        raw_data: dict[str, Any],
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        del user_id, ip_address

        if step_number not in range(1, 8):
            raise BadRequestError(f"Invalid step number: {step_number}")

        restaurante = await self.restaurante_repo.get(restaurant_id)
        if not restaurante:
            raise NotFoundError("Onboarding session", restaurant_id)

        if restaurante.onboarding_estado == ONBOARDING_ESTADO_ENVIADO:
            raise BadRequestError("Onboarding already submitted and cannot be modified")

        schema_cls = STEP_SCHEMA_MAP[step_number]
        sanitized = sanitize_dict(raw_data)
        validated = schema_cls.model_validate(sanitized)
        validated_dict = validated.model_dump(mode="json")

        await self._persist_step_to_table(restaurant_id, step_number, validated)

        onboarding_datos = _merge_step_data(restaurante.onboarding_datos, step_number, validated_dict)
        completed_steps = _steps_completed(onboarding_datos)
        percentage = self.calculate_percentage(completed_steps)
        next_step = min(max(restaurante.onboarding_paso or 1, step_number + 1), 7)
        now = datetime.now(timezone.utc)

        await self.restaurante_repo.update(
            restaurante,
            onboarding_datos=onboarding_datos,
            onboarding_paso=next_step,
            onboarding_pct=percentage,
            onboarding_estado=ONBOARDING_ESTADO_BORRADOR,
            updated_at=now,
        )
        await self.session.commit()
        await _redis_delete(self.redis, _cache_key(restaurant_id))

        return {
            "step": step_number,
            "restaurant_id": restaurant_id,
            "completion_percentage": percentage,
            "steps_completed": completed_steps,
        }

    async def _persist_step_to_table(
        self, restaurant_id: int, step_number: int, validated: Any
    ) -> None:
        restaurante = await self.restaurante_repo.get(restaurant_id)
        if not restaurante:
            return

        if step_number == 1:
            data: Step1BasicInfo = validated
            website_str = str(data.website) if data.website else None
            categoria = await self.categoria_repo.get_or_create(
                RESTAURANT_TYPE_LABELS.get(data.restaurant_type, data.restaurant_type)
            )
            await self.restaurante_repo.update(
                restaurante,
                nombre=data.restaurant_name,
                razon_social=data.legal_name,
                descripcion=data.description,
                sitio_web=website_str,
                redes_sociales=data.social_links,
                id_categoria=categoria.id,
            )
        elif step_number == 2:
            data: Step2Location = validated
            ubicacion = None
            if restaurante.id_ubicacion:
                ubicacion = await self.ubicacion_repo.get(restaurante.id_ubicacion)
            if ubicacion:
                await self.ubicacion_repo.update(
                    ubicacion,
                    pais=data.country,
                    departamento=data.department,
                    ciudad=data.city,
                    barrio=data.address,
                )
            else:
                ubicacion = await self.ubicacion_repo.create(
                    pais=data.country,
                    departamento=data.department,
                    ciudad=data.city,
                    barrio=data.address,
                )
            maps_url = None
            if data.google_maps is not None:
                maps_url = str(data.google_maps)
            elif data.lat is not None and data.lng is not None:
                maps_url = f"https://maps.google.com/?q={data.lat},{data.lng}"
            await self.restaurante_repo.update(
                restaurante,
                direccion=data.address,
                id_ubicacion=ubicacion.id,
                google_maps=maps_url,
            )
        elif step_number == 3:
            data: Step3Contact = validated
            await self.restaurante_repo.update(restaurante, telefono=data.phone)
        elif step_number == 4:
            data: Step4Operations = validated
            await self.horario_repo.replace_weekly_schedule(
                restaurant_id,
                opening=data.opening_hours,
                closing=data.closing_hours,
            )
            horarios_label = (
                f"{data.opening_hours.strftime('%H:%M')}-"
                f"{data.closing_hours.strftime('%H:%M')}"
            )
            await self.restaurante_repo.update(
                restaurante,
                horarios=horarios_label,
                capacidad_asientos=data.seating_capacity,
                numero_mesas=data.number_tables,
            )
        elif step_number == 5:
            data: Step5Features = validated
            categoria_ids: list[int] = []
            for cuisine in data.cuisine_types:
                cat = await self.categoria_repo.get_or_create(cuisine.title())
                categoria_ids.append(cat.id)
            await self.restaurante_categoria_repo.replace_for_restaurant(
                restaurant_id, categoria_ids
            )
            if categoria_ids:
                await self.restaurante_repo.update(restaurante, id_categoria=categoria_ids[0])

            etiqueta_ids: list[int] = []
            for service in data.services_offered:
                label = SERVICE_LABELS.get(service, service.replace("_", " ").title())
                etq = await self.etiqueta_repo.get_or_create(label)
                etiqueta_ids.append(etq.id)
            await self.restaurante_etiqueta_repo.replace_for_restaurant(
                restaurant_id, etiqueta_ids
            )
            if etiqueta_ids:
                await self.restaurante_repo.update(restaurante, id_etiqueta=etiqueta_ids[0])

            await self.restaurante_tipo_reserva_repo.replace_for_restaurant(
                restaurant_id, list(data.reservation_types)
            )
        elif step_number == 6:
            data: Step6Files = validated
            base = settings.STORAGE_URL or "https://storage.example.com"
            if data.logo_key:
                logo_url = urljoin(base, f"/{data.logo_key}")
                await self.restaurante_repo.update(restaurante, imagen_destacada=logo_url)
            covers = [
                {"url": urljoin(base, f"/{key}"), "storage_key": key}
                for key in data.cover_image_keys
            ]
            if covers:
                await self.imagen_repo.replace_covers(restaurant_id, covers)
        elif step_number == 7:
            data: Step7Plan = validated
            await self.suscripcion_repo.upsert(
                restaurant_id,
                plan=data.plan,
                ciclo_facturacion=data.billing_cycle,
                estado="trial",
            )

    def calculate_percentage(self, steps_completed: list[int]) -> float:
        completed_set = set(steps_completed)
        required_done = len(REQUIRED_STEPS & completed_set)
        optional_done = len(OPTIONAL_STEPS & completed_set)
        required_pct = (required_done / len(REQUIRED_STEPS)) * REQUIRED_WEIGHT
        optional_pct = (optional_done / len(OPTIONAL_STEPS)) * OPTIONAL_WEIGHT
        return round(required_pct + optional_pct, 1)

    async def get_status(self, restaurant_id: int) -> OnboardingStatusResponse:
        cache_key = _cache_key(restaurant_id)
        cached = await _redis_get(self.redis, cache_key)
        if cached:
            return OnboardingStatusResponse(**json.loads(cached))

        restaurante = await self.restaurante_repo.get(restaurant_id)
        if not restaurante or restaurante.onboarding_estado is None:
            raise NotFoundError("Onboarding session", restaurant_id)

        completed_steps = _steps_completed(restaurante.onboarding_datos)
        updated = restaurante.updated_at.isoformat() if restaurante.updated_at else None

        response = OnboardingStatusResponse(
            restaurant_id=restaurant_id,
            current_step=restaurante.onboarding_paso or 1,
            completion_percentage=float(restaurante.onboarding_pct or 0),
            status=_api_status(restaurante.onboarding_estado),
            steps_completed=completed_steps,
            last_saved_at=updated,
        )

        await _redis_setex(
            self.redis,
            cache_key,
            settings.REDIS_TTL_ONBOARDING_STATUS,
            response.model_dump_json(),
        )
        return response

    async def submit_onboarding(
        self,
        restaurant_id: int,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        del user_id, ip_address

        restaurante = await self.restaurante_repo.get(restaurant_id)
        if not restaurante:
            raise NotFoundError("Onboarding session", restaurant_id)

        if restaurante.onboarding_estado == ONBOARDING_ESTADO_ENVIADO:
            raise BadRequestError("Onboarding already submitted")

        completed_steps = set(_steps_completed(restaurante.onboarding_datos))
        missing_required = REQUIRED_STEPS - completed_steps
        if missing_required:
            raise BadRequestError(
                f"Required steps not completed: {sorted(missing_required)}. "
                "Steps 1, 2, and 3 are mandatory."
            )

        now = datetime.now(timezone.utc)
        await self.restaurante_repo.update(
            restaurante,
            onboarding_estado=ONBOARDING_ESTADO_ENVIADO,
            onboarding_enviado_en=now,
            onboarding_pct=self.calculate_percentage(list(completed_steps)),
            activo=True,
            updated_at=now,
        )
        await self.session.commit()
        await _redis_delete(self.redis, _cache_key(restaurant_id))

        logger.info("Onboarding submitted for restaurant_id=%s", restaurant_id)
        return {
            "restaurant_id": restaurant_id,
            "status": API_STATUS_SUBMITTED,
            "message": "Onboarding submitted successfully. Our team will review it shortly.",
        }

    async def get_full_data(self, restaurant_id: int) -> FullOnboardingDataResponse:
        restaurante = await self.restaurante_repo.get(restaurant_id)
        if not restaurante:
            raise NotFoundError("Onboarding session", restaurant_id)

        documents = await self.documento_repo.list_by_restaurant(restaurant_id)
        images = await self.imagen_repo.list_by_restaurant(restaurant_id)
        subscription = await self.suscripcion_repo.get_by(id_restaurante=restaurant_id)

        return FullOnboardingDataResponse(
            restaurant_id=restaurant_id,
            status=_api_status(restaurante.onboarding_estado),
            current_step=restaurante.onboarding_paso or 1,
            completion_percentage=float(restaurante.onboarding_pct or 0),
            profile=RestaurantProfileOut.from_restaurante(restaurante),
            contact=RestaurantContactOut.from_restaurante(restaurante),
            features=RestaurantFeatureOut.from_restaurante(restaurante),
            documents=[RestaurantDocumentOut.from_documento(d) for d in documents],
            images=[RestaurantImageOut.from_imagen(i) for i in images],
            subscription=RestaurantSubscriptionOut.from_suscripcion(subscription)
            if subscription
            else None,
        )
