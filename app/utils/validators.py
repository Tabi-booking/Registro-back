from __future__ import annotations

import re

import phonenumbers

ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_DOC_MIME_TYPES = frozenset({"application/pdf", "image/jpeg", "image/png"})
ALL_ALLOWED_MIME_TYPES = ALLOWED_IMAGE_MIME_TYPES | ALLOWED_DOC_MIME_TYPES

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def validate_phone_number(phone: str) -> str:
    """Validate and normalize a phone number to E.164 format."""
    try:
        parsed = phonenumbers.parse(phone, None)
    except phonenumbers.NumberParseException:
        raise ValueError(
            f"Invalid phone number: '{phone}'. Must be in E.164 format (e.g., +573001234567)."
        )
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Phone number '{phone}' is not a valid international number.")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def validate_mime_type(mime_type: str, allowed: frozenset[str] | None = None) -> bool:
    """Return True if mime_type is in the allowed set."""
    allowed_set = allowed or ALL_ALLOWED_MIME_TYPES
    return mime_type in allowed_set


def validate_file_size(size_bytes: int, max_bytes: int = MAX_FILE_SIZE_BYTES) -> bool:
    """Return True if file size is within limit."""
    return 0 < size_bytes <= max_bytes


def validate_business_hours(opening: str, closing: str) -> bool:
    """
    Validate that closing time is after opening time.
    Times should be in HH:MM format.
    """
    from datetime import time

    def _parse(t: str) -> time:
        parts = t.split(":")
        return time(int(parts[0]), int(parts[1]))

    try:
        o = _parse(opening)
        c = _parse(closing)
    except (ValueError, IndexError):
        raise ValueError("Times must be in HH:MM format")

    if c <= o:
        raise ValueError("Closing time must be after opening time")
    return True


def validate_storage_key(key: str) -> bool:
    """Validate that a storage key has valid format (no path traversal)."""
    if not key:
        return False
    pattern = r"^[a-zA-Z0-9_\-./]+$"
    if not re.match(pattern, key):
        return False
    if ".." in key:
        return False
    return True
