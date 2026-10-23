"""OIDC (Keycloak) adapter behind the IdentityProvider port.

Everything provider specific is runtime configuration: issuer, client and
redirect URI come from settings, endpoints and signing keys from discovery and
JWKS. The ID token is validated here and discarded. Access, refresh and ID
tokens never leave this module; only an ``AuthenticatedIdentity`` does.
"""

from __future__ import annotations

import hmac
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode, urlparse

import httpx
import jwt

from .idp import (
    AuthorizationRequest,
    IdentityProviderError,
    IdentityProviderUnavailable,
)
from .session import AuthenticatedIdentity

ENV_PREFIX = "OPERATIONS_BFF_OIDC_"
CALLBACK_PATH = "/v1/session/callback"
ALLOWED_ALGORITHMS = frozenset({"RS256", "RS384", "RS512", "PS256", "ES256", "ES384"})
REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub"]
MIN_JWKS_REFRESH = timedelta(seconds=30)


def _require_https(value: str, name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{name} must be an https URL")


@dataclass(frozen=True)
class OidcSettings:
    """Explicit runtime settings. The secret is optional (public client + PKCE)."""

    issuer: str
    client_id: str
    redirect_uri: str
    environment_id: str
    client_secret: str | None = field(default=None, repr=False)
    scopes: tuple[str, ...] = ("openid",)
    roles_claim: tuple[str, ...] = ("realm_access", "roles")
    algorithms: tuple[str, ...] = ("RS256",)
    clock_skew: timedelta = timedelta(seconds=30)
    metadata_ttl: timedelta = timedelta(hours=1)
    http_timeout: float = 5.0

    def __post_init__(self) -> None:
        _require_https(self.issuer, "issuer")
        _require_https(self.redirect_uri, "redirect_uri")
        if not urlparse(self.redirect_uri).path.endswith(CALLBACK_PATH):
            raise ValueError(f"redirect_uri must end with {CALLBACK_PATH}")
        for name in ("client_id", "environment_id"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if "openid" not in self.scopes:
            raise ValueError("scopes must include openid")
        if not self.algorithms or not set(self.algorithms) <= ALLOWED_ALGORITHMS:
            raise ValueError("algorithms must be asymmetric signature algorithms")
        if not self.roles_claim:
            raise ValueError("roles_claim must not be empty")
        if self.http_timeout <= 0 or self.clock_skew < timedelta(0):
            raise ValueError("timeout and clock skew must be non-negative")

    @classmethod
    def from_environ(cls, environ: Mapping[str, str]) -> OidcSettings:
        def get(name: str) -> str | None:
            value = environ.get(ENV_PREFIX + name)
            return value.strip() if value and value.strip() else None

        required = ("ISSUER", "CLIENT_ID", "REDIRECT_URI", "ENVIRONMENT_ID")
        missing = [ENV_PREFIX + n for n in required if get(n) is None]
        if missing:
            raise ValueError("missing OIDC settings: " + ", ".join(missing))
        scopes = get("SCOPES")
        roles = get("ROLES_CLAIM")
        algorithms = get("ALGORITHMS")
        return cls(
            issuer=get("ISSUER") or "",
            client_id=get("CLIENT_ID") or "",
            redirect_uri=get("REDIRECT_URI") or "",
            environment_id=get("ENVIRONMENT_ID") or "",
            client_secret=get("CLIENT_SECRET"),
            scopes=tuple(scopes.split()) if scopes else ("openid",),
            roles_claim=tuple(roles.split(".")) if roles else ("realm_access", "roles"),
            algorithms=tuple(algorithms.split()) if algorithms else ("RS256",),
        )


@dataclass(frozen=True)
class _Metadata:
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    fetched_at: datetime


@dataclass(frozen=True)
class _Keys:
    keyset: jwt.PyJWKSet
    fetched_at: datetime


class OidcIdentityProvider:
    def __init__(
        self,
        settings: OidcSettings,
        client: httpx.Client,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._clock = clock or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()
        self._metadata: _Metadata | None = None
        self._keys: _Keys | None = None

    # -- port ---------------------------------------------------------------

    def authorization_url(self, request: AuthorizationRequest) -> str:
        metadata = self._discover()
        s = self._settings
        query = urlencode(
            {
                "response_type": "code",
                "client_id": s.client_id,
                "redirect_uri": s.redirect_uri,
                "scope": " ".join(s.scopes),
                "state": request.state,
                "code_challenge": request.code_challenge,
                "code_challenge_method": request.code_challenge_method,
                "nonce": request.nonce,
            }
        )
        return f"{metadata.authorization_endpoint}?{query}"

    def complete(
        self, *, code: str, code_verifier: str, nonce: str
    ) -> AuthenticatedIdentity:
        id_token = self._exchange(code, code_verifier)
        claims = self._validate(id_token, nonce)
        return self._identity(claims)

    # -- discovery and keys -------------------------------------------------

    def _fresh(self, fetched_at: datetime) -> bool:
        return self._clock() - fetched_at < self._settings.metadata_ttl

    def _get_json(self, url: str) -> dict[str, Any]:
        try:
            response = self._client.get(url, timeout=self._settings.http_timeout)
        except httpx.HTTPError:
            raise IdentityProviderUnavailable from None
        if response.status_code != 200:
            raise IdentityProviderUnavailable
        try:
            document = response.json()
        except ValueError:
            raise IdentityProviderUnavailable from None
        if not isinstance(document, dict):
            raise IdentityProviderUnavailable
        return document  # pyright: ignore[reportUnknownVariableType]

    def _discover(self) -> _Metadata:
        with self._lock:
            if self._metadata and self._fresh(self._metadata.fetched_at):
                return self._metadata
            issuer = self._settings.issuer
            doc = self._get_json(
                issuer.rstrip("/") + "/.well-known/openid-configuration"
            )
            if doc.get("issuer") != issuer:
                raise IdentityProviderUnavailable  # mix-up or misconfiguration
            methods = doc.get("code_challenge_methods_supported")
            if methods is not None and "S256" not in methods:
                raise IdentityProviderUnavailable
            endpoints: list[str] = []
            for name in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
                value = doc.get(name)
                if not isinstance(value, str) or urlparse(value).scheme != "https":
                    raise IdentityProviderUnavailable
                endpoints.append(value)
            self._metadata = _Metadata(*endpoints, fetched_at=self._clock())
            return self._metadata

    def _load_keys(self, metadata: _Metadata) -> _Keys:
        document = self._get_json(metadata.jwks_uri)
        try:
            keyset = jwt.PyJWKSet.from_dict(document)  # pyright: ignore[reportArgumentType]
        except jwt.PyJWTError:
            raise IdentityProviderUnavailable from None
        self._keys = _Keys(keyset, self._clock())
        return self._keys

    @staticmethod
    def _find(keys: _Keys, kid: str) -> Any:
        return next((k.key for k in keys.keyset.keys if k.key_id == kid), None)

    def _signing_key(self, kid: str) -> Any:
        metadata = self._discover()
        with self._lock:
            keys = self._keys
            if keys is None or not self._fresh(keys.fetched_at):
                keys = self._load_keys(metadata)
            key = self._find(keys, kid)
            # An unknown kid may mean rotation: refetch, but never in a tight loop.
            if key is None and self._clock() - keys.fetched_at >= MIN_JWKS_REFRESH:
                key = self._find(self._load_keys(metadata), kid)
            if key is None:
                raise IdentityProviderError
            return key

    # -- code exchange and validation ---------------------------------------

    def _exchange(self, code: str, code_verifier: str) -> str:
        s = self._settings
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": s.redirect_uri,
            "client_id": s.client_id,
            "code_verifier": code_verifier,
        }
        if s.client_secret:
            form["client_secret"] = s.client_secret
        endpoint = self._discover().token_endpoint
        try:
            response = self._client.post(
                endpoint,
                data=form,
                headers={"Accept": "application/json"},
                timeout=s.http_timeout,
            )
        except httpx.HTTPError:
            raise IdentityProviderUnavailable from None
        if response.status_code >= 500:
            raise IdentityProviderUnavailable
        if response.status_code != 200:
            raise IdentityProviderError
        try:
            body = response.json()
        except ValueError:
            raise IdentityProviderError from None
        token = body.get("id_token") if isinstance(body, dict) else None  # pyright: ignore[reportUnknownMemberType]
        if not isinstance(token, str) or not token:
            raise IdentityProviderError
        # access_token and refresh_token are deliberately never read.
        return token

    def _validate(self, id_token: str, nonce: str) -> dict[str, Any]:
        s = self._settings
        try:
            header = jwt.get_unverified_header(id_token)
            kid = header.get("kid")
            if header.get("alg") not in s.algorithms or not isinstance(kid, str):
                raise IdentityProviderError
            key = self._signing_key(kid)
            claims: dict[str, Any] = jwt.decode(
                id_token,
                key=key,
                algorithms=list(s.algorithms),
                audience=s.client_id,
                issuer=s.issuer,
                leeway=s.clock_skew,
                options={"require": REQUIRED_CLAIMS},
            )
        except jwt.PyJWTError:
            raise IdentityProviderError from None
        audience = claims.get("aud")
        many = isinstance(audience, list) and len(audience) > 1  # pyright: ignore[reportUnknownArgumentType]
        if many and claims.get("azp") != s.client_id:
            raise IdentityProviderError
        presented = claims.get("nonce")
        if not isinstance(presented, str) or not hmac.compare_digest(
            presented.encode(), nonce.encode()
        ):
            raise IdentityProviderError
        if not isinstance(claims.get("sub"), str) or not claims["sub"].strip():
            raise IdentityProviderError
        return claims

    def _identity(self, claims: dict[str, Any]) -> AuthenticatedIdentity:
        node: Any = claims
        for part in self._settings.roles_claim:
            node = node.get(part) if isinstance(node, dict) else None
        roles = node if isinstance(node, list) else []
        names = sorted({r for r in roles if isinstance(r, str) and r.strip()})  # pyright: ignore[reportUnknownVariableType]
        display = next(
            (
                claims[k]
                for k in ("name", "preferred_username", "email")
                if isinstance(claims.get(k), str) and claims[k].strip()
            ),
            claims["sub"],
        )
        return AuthenticatedIdentity(
            subject=claims["sub"],
            display_name=display,
            roles=tuple(names),
            environment_id=self._settings.environment_id,
        )
