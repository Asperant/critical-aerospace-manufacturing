"""Opaque server-side session handling. No tokens ever leave the server."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol

from .config import SessionConfig
from .errors import Unauthorized


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """What a later OIDC adapter hands over after validating the provider.

    Deliberately holds no access, refresh or ID token: those stay in the adapter.
    """

    subject: str
    display_name: str
    roles: tuple[str, ...]
    environment_id: str


@dataclass(frozen=True)
class SessionRecord:
    session_id: str
    identity: AuthenticatedIdentity
    authenticated_at: datetime
    expires_at: datetime
    issued_at: datetime
    last_seen_at: datetime
    csrf_token: str


class SessionStore(Protocol):
    """Storage port; the in-memory adapter is the only one so far."""

    def put(self, key: str, record: SessionRecord) -> None: ...

    def get(self, key: str) -> SessionRecord | None: ...

    def delete(self, key: str) -> None: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._records: dict[str, SessionRecord] = {}

    def put(self, key: str, record: SessionRecord) -> None:
        self._records[key] = record

    def get(self, key: str) -> SessionRecord | None:
        return self._records.get(key)

    def delete(self, key: str) -> None:
        self._records.pop(key, None)


def store_key(session_id: str) -> str:
    """Records are keyed by a digest so the store never holds a usable cookie."""
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def new_opaque_id() -> str:
    return secrets.token_urlsafe(32)


class SessionManager:
    def __init__(self, store: SessionStore, config: SessionConfig | None = None):
        self._store = store
        self.config = config or SessionConfig()

    def create(
        self,
        identity: AuthenticatedIdentity,
        now: datetime,
        previous_session_id: str | None = None,
    ) -> SessionRecord:
        """Establish a session; always a fresh id, and any prior one is ended."""
        if previous_session_id is not None:
            self.invalidate(previous_session_id)
        return self._issue(identity, now, now, now + self.config.absolute_ttl)

    def resolve(self, session_id: str | None, now: datetime) -> SessionRecord:
        """Return the live session or raise Unauthorized. Idle time slides."""
        if not session_id:
            raise Unauthorized("Authentication required")
        record = self._store.get(store_key(session_id))
        if record is None or not hmac.compare_digest(
            record.session_id.encode(), session_id.encode()
        ):
            raise Unauthorized("Authentication required")
        idle_deadline = record.last_seen_at + self.config.idle_ttl
        if now >= record.expires_at or now >= idle_deadline:
            self._store.delete(store_key(session_id))
            raise Unauthorized("Session expired")
        record = replace(record, last_seen_at=now)
        self._store.put(store_key(session_id), record)
        return record

    def needs_rotation(self, record: SessionRecord, now: datetime) -> bool:
        return now - record.issued_at >= self.config.rotate_after

    def rotate(self, session_id: str, now: datetime) -> SessionRecord:
        """New id and CSRF token; the old id dies and the absolute expiry stays."""
        record = self.resolve(session_id, now)
        self._store.delete(store_key(session_id))
        return self._issue(
            record.identity, record.authenticated_at, now, record.expires_at
        )

    def invalidate(self, session_id: str) -> None:
        self._store.delete(store_key(session_id))

    def _issue(
        self,
        identity: AuthenticatedIdentity,
        authenticated_at: datetime,
        now: datetime,
        expires_at: datetime,
    ) -> SessionRecord:
        record = SessionRecord(
            session_id=new_opaque_id(),
            identity=identity,
            authenticated_at=authenticated_at,
            expires_at=expires_at,
            issued_at=now,
            last_seen_at=now,
            csrf_token=new_opaque_id(),
        )
        self._store.put(store_key(record.session_id), record)
        return record


def format_timestamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def session_view(record: SessionRecord) -> dict[str, Any]:
    """Browser-visible ``bff.session.v1`` body; carries no credential."""
    identity = record.identity
    return {
        "contract_version": "bff.session.v1",
        "actor": {
            "actor_id": identity.subject,
            "display_name": identity.display_name,
            "roles": list(identity.roles),
            "derived_from": "SESSION",
        },
        "environment_id": identity.environment_id,
        "authenticated_at": format_timestamp(record.authenticated_at),
        "expires_at": format_timestamp(record.expires_at),
        "csrf_token": record.csrf_token,
    }
