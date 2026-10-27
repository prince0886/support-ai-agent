"""Small shared helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None) -> str | None:
    """Serialize datetimes as explicit UTC ISO-8601 so the browser can parse them."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def first_name(full_name: str | None) -> str | None:
    if not full_name:
        return None
    candidate = full_name.strip().split()[0]
    return candidate or None