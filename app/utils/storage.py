from __future__ import annotations

import logging
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.exceptions import BadRequestError, StorageError

logger = logging.getLogger(__name__)


def storage_configured() -> bool:
    key = settings.SUPABASE_SERVICE_KEY.strip()
    return bool(settings.SUPABASE_URL and key and not key.startswith("your_"))


def public_url(storage_key: str) -> str:
    """Public URL for a file in Supabase Storage."""
    base = (settings.SUPABASE_URL or settings.STORAGE_URL).rstrip("/")
    bucket = settings.STORAGE_BUCKET
    encoded_key = "/".join(quote(part, safe="") for part in storage_key.split("/"))
    return f"{base}/storage/v1/object/public/{bucket}/{encoded_key}"


def validate_restaurant_storage_key(storage_key: str, restaurant_id: int) -> None:
    prefix = f"restaurants/{restaurant_id}/"
    if not storage_key.startswith(prefix):
        raise BadRequestError(f"Invalid storage key for restaurant {restaurant_id}")


def _absolute_upload_url(upload_url: str) -> str:
    """Supabase sign API may return a path-only URL; normalize to an absolute URL."""
    if upload_url.startswith(("http://", "https://")):
        return upload_url
    base = settings.SUPABASE_URL.rstrip("/")
    path = upload_url if upload_url.startswith("/") else f"/{upload_url}"
    if path.startswith("/storage/v1/"):
        return f"{base}{path}"
    return f"{base}/storage/v1{path}"


def _storage_error_message(status_code: int, body: str) -> str:
    bucket = settings.STORAGE_BUCKET
    if status_code == 400 and "does not exist" in body:
        return (
            f"Storage bucket '{bucket}' was not found in Supabase. "
            "Create it in Storage (public, with upload policies) or run the setup script."
        )
    return "Could not generate upload URL"


async def create_signed_upload_url(storage_key: str) -> tuple[str, dict[str, str], int]:
    """
    Returns (upload_url, fields/headers, expires_in_seconds).
    Uses Supabase signed upload when configured; otherwise returns a direct object URL.
    """
    if not storage_configured():
        raise StorageError(
            "File uploads are not configured. Set SUPABASE_SERVICE_KEY in .env "
            "(Supabase → Settings → API → service_role key) and ensure bucket "
            f"'{settings.STORAGE_BUCKET}' exists."
        )

    sign_url = (
        f"{settings.SUPABASE_URL.rstrip('/')}/storage/v1/object/upload/sign/"
        f"{settings.STORAGE_BUCKET}/{storage_key}"
    )
    headers = {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
        "apikey": settings.SUPABASE_SERVICE_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(sign_url, headers=headers)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        logger.error(
            "Supabase signed upload failed: status=%s body=%s key=%s",
            exc.response.status_code,
            body,
            storage_key,
        )
        raise StorageError(
            _storage_error_message(exc.response.status_code, body)
        ) from exc
    except httpx.HTTPError as exc:
        logger.exception("Failed to create Supabase signed upload URL for key=%s", storage_key)
        raise StorageError("Could not generate upload URL") from exc

    upload_url = data.get("url") or data.get("signedUrl") or ""
    token = data.get("token", "")
    if not upload_url:
        raise StorageError("Supabase did not return an upload URL")

    upload_url = _absolute_upload_url(upload_url)

    fields: dict[str, str] = {}
    if token:
        fields["token"] = token
        fields["Authorization"] = f"Bearer {token}"
    return upload_url, fields, 3600
