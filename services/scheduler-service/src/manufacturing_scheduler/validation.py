"""Strict scalar validation shared by the package modules."""

from __future__ import annotations

from manufacturing_scheduler.errors import SchedulerError


def require_int(
    value: object,
    name: str,
    *,
    minimum: int,
    error: type[SchedulerError],
    maximum: int | None = None,
) -> int:
    """Return ``value`` if it is a real ``int`` (not ``bool``) within its range."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise error(f"{name} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise error(f"{name} must be >= {minimum}, got {value}")
    if maximum is not None and value > maximum:
        raise error(f"{name} must be <= {maximum}, got {value}")
    return value


def require_text(value: object, name: str, *, error: type[SchedulerError]) -> str:
    """A non-empty string with no surrounding whitespace."""
    if not isinstance(value, str):
        raise error(f"{name} must be a str, got {type(value).__name__}")
    if not value or value != value.strip():
        raise error(f"{name} must be non-empty without surrounding whitespace")
    return value
