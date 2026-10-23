"""Bounded session lifetime configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Literal

MAX_ABSOLUTE_TTL = timedelta(hours=12)
COOKIE_NAME = "cap_session"
CSRF_HEADER = "X-CSRF-Token"
LOGIN_COOKIE_NAME = "cap_login"
MAX_LOGIN_TTL = timedelta(minutes=15)


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


@dataclass(frozen=True)
class CookieSettings:
    """Session cookie policy. HttpOnly and Secure are always on and not settable.

    ``same_site`` has no default: the owner chooses Strict or Lax. The cookie
    lifetime is taken from the session itself, never fixed here.
    """

    same_site: Literal["strict", "lax"]

    def __post_init__(self) -> None:
        if self.same_site not in ("strict", "lax"):
            raise ValueError("same_site must be 'strict' or 'lax'")


@dataclass(frozen=True)
class LoginConfig:
    """Bounds for pending login transactions."""

    ttl: timedelta = timedelta(minutes=10)
    max_pending: int = 1000

    def __post_init__(self) -> None:
        if not timedelta(0) < self.ttl <= MAX_LOGIN_TTL:
            raise ValueError("ttl must be positive and at most 15 minutes")
        if self.max_pending < 1:
            raise ValueError("max_pending must be at least 1")
