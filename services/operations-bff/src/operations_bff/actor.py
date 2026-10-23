"""Server-derived ActorContext and rejection of browser-supplied authority."""

from __future__ import annotations

import hmac
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .config import COOKIE_NAME, CSRF_HEADER
from .errors import BadRequest, Forbidden
from .session import SessionManager, SessionRecord

STATE_CHANGING = frozenset({"POST", "PUT", "PATCH", "DELETE"})
# Mirrors the contract's command ``parameters`` key guard (case-insensitive prefix).
AUTHORITY_KEY = re.compile(
    r"^(actor|user|role|permission|principal|identity|session|csrf)", re.IGNORECASE
)
AUTHORITY_HEADERS = frozenset(
    {"x-actor", "x-actor-id", "x-user", "x-user-id", "x-role", "x-roles", "x-identity"}
)


@dataclass(frozen=True)
class ActorContext:
    """Built from the session only. ``world_id`` is the forwarded request binding."""

    actor_id: str
    roles: tuple[str, ...]
    environment_id: str
    world_id: str | None
    derived_from: str = "SESSION"


@dataclass(frozen=True)
class Authenticated:
    session: SessionRecord
    actor: ActorContext


def reject_browser_authority(value: Any, *, where: str = "payload") -> None:
    """Refuse any actor, role or identity key at any depth (400)."""
    if isinstance(value, Mapping):
        for key, item in value.items():  # pyright: ignore[reportUnknownVariableType]
            if AUTHORITY_KEY.match(str(key)):  # pyright: ignore[reportUnknownArgumentType]
                raise BadRequest(f"{where} must not carry authority field {key!r}")
            reject_browser_authority(item, where=where)
    elif isinstance(value, list):
        for item in value:  # pyright: ignore[reportUnknownVariableType]
            reject_browser_authority(item, where=where)


def derive_actor_context(record: SessionRecord, world_id: str | None) -> ActorContext:
    identity = record.identity
    return ActorContext(
        actor_id=identity.subject,
        roles=identity.roles,
        environment_id=identity.environment_id,
        world_id=world_id,
    )


def authenticate_request(
    manager: SessionManager,
    *,
    method: str,
    cookies: Mapping[str, str],
    headers: Mapping[str, str],
    now: datetime,
    world_id: str | None = None,
) -> Authenticated:
    """401 before 403: an anonymous caller learns nothing about CSRF."""
    record = manager.resolve(cookies.get(COOKIE_NAME), now)
    lowered = {name.lower(): value for name, value in headers.items()}
    for name in lowered:
        if name in AUTHORITY_HEADERS:
            raise BadRequest(f"header {name!r} is not accepted as authority")
    if method.upper() in STATE_CHANGING:
        presented = lowered.get(CSRF_HEADER.lower(), "")
        if not presented or not hmac.compare_digest(
            presented.encode(), record.csrf_token.encode()
        ):
            raise Forbidden("CSRF token missing or invalid")
    return Authenticated(record, derive_actor_context(record, world_id))
