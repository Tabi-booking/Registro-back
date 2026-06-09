from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.tabi import (
    DocumentoRestaurante,
    Restaurante,
    RestauranteImagen,
    SuscripcionRestaurante,
)


class RestaurantProfileOut(BaseModel):
    restaurant_id: int
    legal_name: str | None
    restaurant_type: str | None
    description: str | None
    website: str | None
    social_links: dict | None

    @classmethod
    def from_restaurante(cls, restaurante: Restaurante) -> RestaurantProfileOut:
        step1 = (restaurante.onboarding_datos or {}).get("paso_1", {})
        return cls(
            restaurant_id=restaurante.id,
            legal_name=restaurante.razon_social,
            restaurant_type=step1.get("restaurant_type"),
            description=restaurante.descripcion,
            website=restaurante.sitio_web,
            social_links=restaurante.redes_sociales,
        )


class RestaurantContactOut(BaseModel):
    restaurant_id: int
    owner_name: str | None
    email: str | None
    phone: str | None

    @classmethod
    def from_restaurante(cls, restaurante: Restaurante) -> RestaurantContactOut:
        step3 = (restaurante.onboarding_datos or {}).get("paso_3", {})
        return cls(
            restaurant_id=restaurante.id,
            owner_name=step3.get("owner_name"),
            email=step3.get("email"),
            phone=restaurante.telefono,
        )


class RestaurantFeatureOut(BaseModel):
    restaurant_id: int
    reservation_types: list[str] | None
    cuisine_types: list[str] | None
    services_offered: list[str] | None
    seating_capacity: int | None
    number_tables: int | None

    @classmethod
    def from_restaurante(cls, restaurante: Restaurante) -> RestaurantFeatureOut:
        step5 = (restaurante.onboarding_datos or {}).get("paso_5", {})
        return cls(
            restaurant_id=restaurante.id,
            reservation_types=step5.get("reservation_types"),
            cuisine_types=step5.get("cuisine_types"),
            services_offered=step5.get("services_offered"),
            seating_capacity=restaurante.capacidad_asientos,
            number_tables=restaurante.numero_mesas,
        )


class RestaurantDocumentOut(BaseModel):
    id: int
    restaurant_id: int
    document_type: str
    file_url: str
    file_name: str | None
    file_size: int | None
    mime_type: str | None
    storage_key: str | None
    uploaded_at: datetime | None

    @classmethod
    def from_documento(cls, doc: DocumentoRestaurante) -> RestaurantDocumentOut:
        return cls(
            id=doc.id,
            restaurant_id=doc.id_restaurante,
            document_type=doc.tipo,
            file_url=doc.url,
            file_name=doc.nombre_archivo,
            file_size=doc.tamano_bytes,
            mime_type=doc.mime_type,
            storage_key=doc.storage_key,
            uploaded_at=doc.creado_en,
        )


class RestaurantImageOut(BaseModel):
    id: int
    restaurant_id: int
    url: str
    storage_key: str | None
    orden: int

    @classmethod
    def from_imagen(cls, img: RestauranteImagen) -> RestaurantImageOut:
        return cls(
            id=img.id,
            restaurant_id=img.id_restaurante,
            url=img.url,
            storage_key=img.storage_key,
            orden=img.orden,
        )


class RestaurantSubscriptionOut(BaseModel):
    id: int
    restaurant_id: int
    plan: str
    billing_cycle: str
    status: str
    started_at: datetime | None
    expires_at: datetime | None

    @classmethod
    def from_suscripcion(cls, sub: SuscripcionRestaurante) -> RestaurantSubscriptionOut:
        return cls(
            id=sub.id,
            restaurant_id=sub.id_restaurante,
            plan=sub.plan,
            billing_cycle=sub.ciclo_facturacion,
            status=sub.estado,
            started_at=sub.inicio_en,
            expires_at=sub.expira_en,
        )


class FullOnboardingDataResponse(BaseModel):
    restaurant_id: int
    status: str
    current_step: int
    completion_percentage: float
    profile: RestaurantProfileOut | None
    contact: RestaurantContactOut | None
    features: RestaurantFeatureOut | None
    documents: list[RestaurantDocumentOut]
    images: list[RestaurantImageOut]
    subscription: RestaurantSubscriptionOut | None
