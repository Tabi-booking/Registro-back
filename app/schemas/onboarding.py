from __future__ import annotations

from datetime import time
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

import phonenumbers


class Step1BasicInfo(BaseModel):
    restaurant_name: str = Field(min_length=3, max_length=100)
    legal_name: str = Field(min_length=2, max_length=255)
    restaurant_type: Literal[
        "casual", "fine_dining", "fast_casual", "cafe", "bar", "food_truck", "other"
    ]
    description: str = Field(max_length=1000)
    website: HttpUrl | None = None
    social_links: dict[str, str] | None = None

    @field_validator("social_links")
    @classmethod
    def validate_social_links(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        if v is None:
            return v
        allowed = {"instagram", "facebook", "twitter", "tiktok", "youtube", "linkedin"}
        for key in v:
            if key not in allowed:
                raise ValueError(f"Unknown social network: {key}. Allowed: {allowed}")
        return v


class Step2Location(BaseModel):
    country: str = Field(min_length=2, max_length=100)
    department: str | None = Field(default=None, max_length=100)
    city: str = Field(min_length=2, max_length=100)
    address: str = Field(min_length=5, max_length=500)
    google_maps: HttpUrl | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)


class Step3Contact(BaseModel):
    owner_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        try:
            parsed = phonenumbers.parse(v, None)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError("Invalid phone number")
        except phonenumbers.NumberParseException:
            raise ValueError(
                "Phone must be in E.164 format (e.g., +573001234567)"
            )
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


class Step4Operations(BaseModel):
    opening_hours: time
    closing_hours: time
    seating_capacity: int = Field(ge=0, le=2000)
    number_tables: int = Field(ge=0, le=500)

    @field_validator("closing_hours")
    @classmethod
    def validate_hours(cls, v: time, info) -> time:
        opening = info.data.get("opening_hours")
        if opening == time(0, 0) and v == time(0, 0):
            return v
        if opening and v <= opening:
            raise ValueError("closing_hours must be after opening_hours")
        return v


class Step5Features(BaseModel):
    reservation_types: list[Literal["online", "phone", "walk_in", "third_party"]] = Field(
        min_length=1
    )
    cuisine_types: list[str] = Field(min_length=1, max_length=5)
    services_offered: list[
        Literal[
            "parking",
            "wifi",
            "terrace",
            "private_room",
            "accessibility",
            "live_music",
            "catering",
            "delivery",
            "takeaway",
        ]
    ]

    @field_validator("cuisine_types")
    @classmethod
    def validate_cuisine_types(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            raise ValueError("Maximum 5 cuisine types allowed")
        return [ct.strip().lower() for ct in v if ct.strip()]


class Step6Files(BaseModel):
    logo_key: str | None = None
    cover_image_keys: list[str] = Field(default_factory=list, max_length=5)
    document_keys: list[str] = Field(default_factory=list)


class Step7Plan(BaseModel):
    plan: Literal["starter", "pro", "elite"]
    billing_cycle: Literal["monthly", "annual"]


StepData = Step1BasicInfo | Step2Location | Step3Contact | Step4Operations | Step5Features | Step6Files | Step7Plan

STEP_SCHEMA_MAP: dict[int, type] = {
    1: Step1BasicInfo,
    2: Step2Location,
    3: Step3Contact,
    4: Step4Operations,
    5: Step5Features,
    6: Step6Files,
    7: Step7Plan,
}


class OnboardingStatusResponse(BaseModel):
    restaurant_id: int
    current_step: int
    completion_percentage: float
    status: str
    steps_completed: list[int]
    last_saved_at: str | None


class OnboardingStartResponse(BaseModel):
    restaurant_id: int
    message: str


class PresignedUrlRequest(BaseModel):
    file_name: str
    content_type: str
    document_type: Literal["logo", "cover", "business_doc"]

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        allowed = {
            "image/jpeg",
            "image/png",
            "image/webp",
            "application/pdf",
        }
        if v not in allowed:
            raise ValueError(f"Content type {v} not allowed. Allowed: {allowed}")
        return v


class PresignedUrlResponse(BaseModel):
    upload_url: str
    storage_key: str
    expires_in: int  # seconds
    fields: dict[str, str] | None = None


class ConfirmUploadRequest(BaseModel):
    storage_key: str
    file_name: str
    file_size: int = Field(gt=0)
    mime_type: str
    document_type: Literal["logo", "cover", "business_doc"]
