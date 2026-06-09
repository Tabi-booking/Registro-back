from __future__ import annotations

import re

import bleach


def strip_html(text: str) -> str:
    """Remove all HTML tags from a string."""
    return bleach.clean(text, tags=[], strip=True)


def sanitize_string(value: str, max_length: int | None = None) -> str:
    """Strip HTML and optionally truncate a string."""
    cleaned = strip_html(value).strip()
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def sanitize_dict(data: dict) -> dict:
    """Recursively sanitize all string values in a dict."""
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = strip_html(value).strip()
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                strip_html(v).strip() if isinstance(v, str) else v for v in value
            ]
        else:
            result[key] = value
    return result


def sanitize_filename(filename: str) -> str:
    """Remove dangerous characters from filenames."""
    # Keep only alphanumeric, dots, dashes, underscores
    name = re.sub(r"[^\w.\-]", "_", filename)
    # Remove leading dots (hidden files)
    name = name.lstrip(".")
    return name or "unnamed"
