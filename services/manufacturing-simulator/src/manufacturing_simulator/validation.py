"""Strict scalar validation shared by the kernel modules."""

from __future__ import annotations

from manufacturing_simulator.errors import (
    InvalidConfigurationError,
    InvalidTimeError,
    SimulatorError,
)


def require_int(
    value: object,
    name: str,
    *,
    minimum: int,
    error: type[SimulatorError],
) -> int:
    """Return ``value`` if it is a real ``int`` (not ``bool``) of at least ``minimum``."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise error(f"{name} must be an int, got {type(value).__name__}")
    if value < minimum:
        raise error(f"{name} must be >= {minimum}, got {value}")
    return value


def require_time(value: object, name: str) -> int:
    """Simulation-relative integer time: a non-negative ``int``."""
    return require_int(value, name, minimum=0, error=InvalidTimeError)


def require_text(value: object, name: str) -> str:
    """A non-empty string with no surrounding whitespace."""
    if not isinstance(value, str):
        raise InvalidConfigurationError(
            f"{name} must be a str, got {type(value).__name__}"
        )
    if not value or value != value.strip():
        raise InvalidConfigurationError(
            f"{name} must be non-empty without surrounding whitespace"
        )
    return value
