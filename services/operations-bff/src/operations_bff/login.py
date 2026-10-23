"""OIDC login transactions: state, PKCE and browser binding, single use."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .config import LoginConfig
from .errors import LoginRejected, Unavailable
from .idp import (
    AuthorizationRequest,
    IdentityProvider,
    IdentityProviderError,
    IdentityProviderUnavailable,
)
from .session import AuthenticatedIdentity, SessionManager, SessionRecord


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def pkce_challenge(verifier: str) -> str:
    raw = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@dataclass(frozen=True)
class LoginTransaction:
    code_verifier: str
    nonce: str
    binding_digest: str
    expires_at: datetime


class LoginStore(Protocol):
    def put(self, key: str, transaction: LoginTransaction) -> None: ...

    def pop(self, key: str) -> LoginTransaction | None:
        """Remove and return in one step, which is what makes state single use."""
        ...

    def purge_expired(self, now: datetime) -> None: ...

    def count(self) -> int: ...


class InMemoryLoginStore:
    def __init__(self) -> None:
        self._items: dict[str, LoginTransaction] = {}

    def put(self, key: str, transaction: LoginTransaction) -> None:
        self._items[key] = transaction

    def pop(self, key: str) -> LoginTransaction | None:
        return self._items.pop(key, None)

    def purge_expired(self, now: datetime) -> None:
        self._items = {k: v for k, v in self._items.items() if now < v.expires_at}

    def count(self) -> int:
        return len(self._items)


@dataclass(frozen=True)
class StartedLogin:
    location: str
    binding: str
    max_age_seconds: int


def _validated(identity: object) -> AuthenticatedIdentity:
    if not isinstance(identity, AuthenticatedIdentity):
        raise LoginRejected("Identity provider returned no validated identity")
    texts = (identity.subject, identity.display_name, identity.environment_id)
    if not all(t.strip() for t in texts) or not all(r.strip() for r in identity.roles):
        raise LoginRejected("Identity provider result is incomplete")
    return identity


class LoginService:
    def __init__(
        self,
        idp: IdentityProvider,
        store: LoginStore,
        sessions: SessionManager,
        config: LoginConfig | None = None,
    ) -> None:
        self._idp = idp
        self._store = store
        self._sessions = sessions
        self.config = config or LoginConfig()

    def start(self, now: datetime) -> StartedLogin:
        self._store.purge_expired(now)
        if self._store.count() >= self.config.max_pending:
            raise Unavailable("Too many pending logins")
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        nonce = secrets.token_urlsafe(32)
        binding = secrets.token_urlsafe(32)
        self._store.put(
            digest(state),
            LoginTransaction(
                code_verifier=verifier,
                nonce=nonce,
                binding_digest=digest(binding),
                expires_at=now + self.config.ttl,
            ),
        )
        location = self._idp.authorization_url(
            AuthorizationRequest(
                state=state, code_challenge=pkce_challenge(verifier), nonce=nonce
            )
        )
        return StartedLogin(location, binding, int(self.config.ttl.total_seconds()))

    def complete(
        self,
        *,
        code: str,
        state: str,
        binding: str | None,
        previous_session_id: str | None,
        now: datetime,
    ) -> SessionRecord:
        # Consumed first: any attempt, good or bad, spends the transaction.
        transaction = self._store.pop(digest(state))
        if transaction is None:
            raise LoginRejected("Login state is unknown or already used")
        if now >= transaction.expires_at:
            raise LoginRejected("Login state expired")
        if not binding or not hmac.compare_digest(
            digest(binding), transaction.binding_digest
        ):
            raise LoginRejected("Login was not started by this browser")
        try:
            identity = self._idp.complete(
                code=code,
                code_verifier=transaction.code_verifier,
                nonce=transaction.nonce,
            )
        except IdentityProviderUnavailable:
            raise Unavailable("Identity provider unavailable") from None
        except IdentityProviderError:
            raise LoginRejected("Identity provider refused the login") from None
        return self._sessions.create(
            _validated(identity), now, previous_session_id=previous_session_id
        )
