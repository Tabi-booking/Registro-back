from __future__ import annotations


def split_full_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]
