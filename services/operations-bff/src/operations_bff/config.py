"""Bounded session lifetime configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

MAX_ABSOLUTE_TTL = timedelta(hours=12)
COOKIE_NAME = "cap_session"
CSRF_HEADER = "X-CSRF-Token"


@dataclass(frozen=True)
class SessionConfig:
    """Lifetimes are bounded; defaults are provisional until the owner sets policy.

    ``absolute_ttl`` is never extended, by activity or by rotation.
    """

    absolute_ttl: timedelta = timedelta(hours=8)
    idle_ttl: timedelta = timedelta(minutes=30)
    rotate_after: timedelta = timedelta(minutes=15)

    def __post_init__(self) -> None:
        zero = timedelta(0)
        if not zero < self.absolute_ttl <= MAX_ABSOLUTE_TTL:
            raise ValueError("absolute_ttl must be positive and at most 12 hours")
        if not zero < self.idle_ttl <= self.absolute_ttl:
            raise ValueError("idle_ttl must be positive and within absolute_ttl")
        if not zero < self.rotate_after <= self.idle_ttl:
            raise ValueError("rotate_after must be positive and within idle_ttl")
