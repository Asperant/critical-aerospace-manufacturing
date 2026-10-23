"""OIDC adapter against a deterministic local HTTP boundary (httpx.MockTransport)."""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from operations_bff.api import create_app
from operations_bff.config import CookieSettings
from operations_bff.idp import (
    AuthorizationRequest,
    IdentityProviderError,
    IdentityProviderUnavailable,
)
from operations_bff.login import (
    InMemoryLoginStore,
    LoginService,
    pkce_challenge,
)
from operations_bff.oidc import OidcIdentityProvider, OidcSettings
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
)
from test_contract_v1 import validator_for

ISSUER = "https://idp.invalid/realms/cap"
CLIENT_ID = "operations-bff"
REDIRECT = "https://cc.invalid/v1/session/callback"
KID = "key-1"
SECRET = "synthetic-client-secret-not-real"
ID_TOKEN_MARKER = "eyJ"  # every compact JWT starts with this
ACCESS = "SYNTHETIC-ACCESS-TOKEN"
REFRESH = "SYNTHETIC-REFRESH-TOKEN"
T0 = datetime(2026, 10, 23, 8, 0, 0, tzinfo=UTC)


def new_key() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


KEY = new_key()
OTHER_KEY = new_key()


def jwks(key: rsa.RSAPrivateKey = KEY, kid: str = KID) -> dict[str, Any]:
    jwk = json.loads(RSAAlgorithm.to_jwk(key.public_key()))
    return {"keys": [{**jwk, "kid": kid, "use": "sig", "alg": "RS256"}]}


def claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    base: dict[str, Any] = {
        "iss": ISSUER,
        "aud": CLIENT_ID,
        "sub": "U-KC-7",
        "name": "Keycloak Operator",
        "nonce": "NONCE-1",
        "iat": now,
        "exp": now + 300,
        "realm_access": {"roles": ["ops-controller", "auditor", "auditor"]},
    }
    base.update(overrides)
    return {k: v for k, v in base.items() if v is not None}


def sign(
    payload: dict[str, Any], key: Any = KEY, kid: str | None = KID, alg: str = "RS256"
) -> str:
    headers = {"kid": kid} if kid else {}
    return jwt.encode(payload, key, algorithm=alg, headers=headers)


class Provider:
    """Local stand-in for the identity provider's HTTP surface."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.token_requests: list[dict[str, list[str]]] = []
        self.discovery: dict[str, Any] = {
            "issuer": ISSUER,
            "authorization_endpoint": ISSUER + "/protocol/openid-connect/auth",
            "token_endpoint": ISSUER + "/protocol/openid-connect/token",
            "jwks_uri": ISSUER + "/protocol/openid-connect/certs",
            "code_challenge_methods_supported": ["plain", "S256"],
        }
        self.discovery_status = 200
        self.keys: dict[str, Any] = jwks()
        self.keys_status = 200
        self.token_status = 200
        self.token_body: Any = None
        self.id_token = ""
        self.error: Exception | None = None

    def handle(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(path)
        if self.error is not None:
            raise self.error
        if path.endswith("/.well-known/openid-configuration"):
            return httpx.Response(self.discovery_status, json=self.discovery)
        if path.endswith("/certs"):
            return httpx.Response(self.keys_status, json=self.keys)
        if path.endswith("/token"):
            self.token_requests.append(parse_qs(request.content.decode()))
            if self.token_body is not None:
                return httpx.Response(self.token_status, content=self.token_body)
            body = {
                "id_token": self.id_token,
                "access_token": ACCESS,
                "refresh_token": REFRESH,
                "token_type": "Bearer",
            }
            return httpx.Response(self.token_status, json=body)
        return httpx.Response(404)


def settings(**overrides: Any) -> OidcSettings:
    values: dict[str, Any] = {
        "issuer": ISSUER,
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "environment_id": "ENV-SYNTHETIC-TEST",
        "client_secret": SECRET,
    }
    values.update(overrides)
    return OidcSettings(**values)


class Rig:
    def __init__(self, **overrides: Any) -> None:
        self.provider = Provider()
        self.now = T0
        self.client = httpx.Client(transport=httpx.MockTransport(self.provider.handle))
        self.adapter = OidcIdentityProvider(
            settings(**overrides), self.client, clock=lambda: self.now
        )

    def complete(self, token: str, nonce: str = "NONCE-1", code: str = "CODE-1"):
        self.provider.id_token = token
        return self.adapter.complete(code=code, code_verifier="V" * 50, nonce=nonce)


def test_settings_come_from_explicit_environment_only() -> None:
    env = {
        "OPERATIONS_BFF_OIDC_ISSUER": ISSUER,
        "OPERATIONS_BFF_OIDC_CLIENT_ID": CLIENT_ID,
        "OPERATIONS_BFF_OIDC_REDIRECT_URI": REDIRECT,
        "OPERATIONS_BFF_OIDC_ENVIRONMENT_ID": "ENV-1",
        "OPERATIONS_BFF_OIDC_CLIENT_SECRET": SECRET,
        "OPERATIONS_BFF_OIDC_ROLES_CLAIM": "resource_access.operations-bff.roles",
    }
    loaded = OidcSettings.from_environ(env)
    assert loaded.client_secret == SECRET
    assert loaded.roles_claim == ("resource_access", "operations-bff", "roles")
    assert SECRET not in repr(loaded)
    assert (
        OidcSettings.from_environ(
            {k: v for k, v in env.items() if "SECRET" not in k}
        ).client_secret
        is None
    )
    with pytest.raises(ValueError) as caught:
        OidcSettings.from_environ({})
    assert "OPERATIONS_BFF_OIDC_ISSUER" in str(caught.value)


@pytest.mark.parametrize(
    "bad",
    [
        {"issuer": "http://idp.invalid/realms/cap"},
        {"redirect_uri": "http://cc.invalid/v1/session/callback"},
        {"redirect_uri": "https://cc.invalid/other"},
        {"client_id": " "},
        {"environment_id": ""},
        {"scopes": ("profile",)},
        {"algorithms": ("none",)},
        {"algorithms": ("HS256",)},
        {"algorithms": ()},
        {"roles_claim": ()},
    ],
)
def test_unsafe_settings_are_refused(bad: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        settings(**bad)


def test_authorization_url_uses_discovery_state_pkce_and_nonce() -> None:
    rig = Rig()
    request = AuthorizationRequest(
        state="STATE-1", code_challenge=pkce_challenge("V" * 50), nonce="NONCE-1"
    )
    url = urlparse(rig.adapter.authorization_url(request))
    assert f"{url.scheme}://{url.netloc}{url.path}" == (
        ISSUER + "/protocol/openid-connect/auth"
    )
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert query == {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT,
        "scope": "openid",
        "state": "STATE-1",
        "code_challenge": pkce_challenge("V" * 50),
        "code_challenge_method": "S256",
        "nonce": "NONCE-1",
    }
    assert SECRET not in url.query
    rig.adapter.authorization_url(request)
    assert rig.provider.calls == ["/realms/cap/.well-known/openid-configuration"]
    rig.now = T0 + timedelta(hours=1)
    rig.adapter.authorization_url(request)
    assert len(rig.provider.calls) == 2  # discovery refreshed after its TTL


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d.update(issuer="https://evil.invalid/realms/cap"),
        lambda d: d.update(token_endpoint="http://idp.invalid/token"),
        lambda d: d.pop("jwks_uri"),
        lambda d: d.update(code_challenge_methods_supported=["plain"]),
    ],
)
def test_bad_discovery_documents_are_refused(mutate: Any) -> None:
    rig = Rig()
    mutate(rig.provider.discovery)
    request = AuthorizationRequest("S", "C", "N")
    with pytest.raises(IdentityProviderUnavailable):
        rig.adapter.authorization_url(request)


def test_discovery_outage_is_unavailable() -> None:
    rig = Rig()
    rig.provider.discovery_status = 503
    with pytest.raises(IdentityProviderUnavailable):
        rig.adapter.authorization_url(AuthorizationRequest("S", "C", "N"))


def test_code_exchange_returns_only_a_validated_identity() -> None:
    rig = Rig()
    identity = rig.complete(sign(claims()))
    assert identity == AuthenticatedIdentity(
        subject="U-KC-7",
        display_name="Keycloak Operator",
        roles=("auditor", "ops-controller"),
        environment_id="ENV-SYNTHETIC-TEST",
    )
    form = rig.provider.token_requests[0]
    assert form["grant_type"] == ["authorization_code"]
    assert form["code"] == ["CODE-1"]
    assert form["code_verifier"] == ["V" * 50]
    assert form["redirect_uri"] == [REDIRECT]
    assert form["client_id"] == [CLIENT_ID]
    assert form["client_secret"] == [SECRET]


def test_public_client_sends_no_secret_and_falls_back_for_display_name() -> None:
    rig = Rig(client_secret=None)
    identity = rig.complete(sign(claims(name=None, preferred_username="op7")))
    assert identity.display_name == "op7"
    assert "client_secret" not in rig.provider.token_requests[0]
    bare = rig.complete(sign(claims(name=None, realm_access=None)))
    assert bare.display_name == "U-KC-7"
    assert bare.roles == ()


def test_roles_claim_path_is_configurable() -> None:
    rig = Rig(roles_claim=("resource_access", "operations-bff", "roles"))
    token = sign(
        claims(
            realm_access={"roles": ["ignored"]},
            resource_access={"operations-bff": {"roles": ["quality-engineer"]}},
        )
    )
    assert rig.complete(token).roles == ("quality-engineer",)


@pytest.mark.parametrize(
    "case",
    [
        "issuer",
        "audience",
        "nonce",
        "no_nonce",
        "expired",
        "not_yet_valid",
        "no_exp",
        "no_sub",
        "bad_signature",
        "unknown_kid",
        "no_kid",
        "multi_aud_no_azp",
        "hs256_confusion",
        "none_alg",
        "garbage",
    ],
)
def test_invalid_id_tokens_are_rejected(case: str) -> None:
    rig = Rig()
    now = int(time.time())
    token: str
    if case == "issuer":
        token = sign(claims(iss="https://evil.invalid/realms/cap"))
    elif case == "audience":
        token = sign(claims(aud="someone-else"))
    elif case == "nonce":
        token = sign(claims(nonce="OTHER"))
    elif case == "no_nonce":
        token = sign(claims(nonce=None))
    elif case == "expired":
        token = sign(claims(iat=now - 900, exp=now - 600))
    elif case == "not_yet_valid":
        token = sign(claims(iat=now + 900, exp=now + 1200, nbf=now + 900))
    elif case == "no_exp":
        token = sign(claims(exp=None))
    elif case == "no_sub":
        token = sign(claims(sub=None))
    elif case == "bad_signature":
        token = sign(claims(), key=OTHER_KEY)
    elif case == "unknown_kid":
        token = sign(claims(), kid="rotated-away")
    elif case == "no_kid":
        token = sign(claims(), kid=None)
    elif case == "multi_aud_no_azp":
        token = sign(claims(aud=[CLIENT_ID, "other"]))
    elif case == "hs256_confusion":
        token = jwt.encode(
            claims(),
            "synthetic-hmac-secret-0123456789abcdef",
            algorithm="HS256",
            headers={"kid": KID},
        )
    elif case == "none_alg":
        token = jwt.encode(
            claims(),
            None,  # pyright: ignore[reportArgumentType]
            algorithm="none",
            headers={"kid": KID},
        )
    else:
        token = "not-a-jwt"
    with pytest.raises(IdentityProviderError):
        rig.complete(token)


def test_unknown_kid_refetches_keys_once_and_not_in_a_tight_loop() -> None:
    rig = Rig()
    rig.complete(sign(claims()))
    key_fetches = lambda: sum(c.endswith("/certs") for c in rig.provider.calls)  # noqa: E731
    assert key_fetches() == 1
    rotated = sign(claims(), key=OTHER_KEY, kid="key-2")
    with pytest.raises(IdentityProviderError):
        rig.complete(rotated)
    assert key_fetches() == 1  # too soon to refetch
    rig.now = T0 + timedelta(minutes=1)
    rig.provider.keys = {"keys": jwks()["keys"] + jwks(OTHER_KEY, "key-2")["keys"]}
    assert rig.complete(rotated).subject == "U-KC-7"
    assert key_fetches() == 2


def test_multiple_audiences_are_allowed_when_azp_matches() -> None:
    rig = Rig()
    token = sign(claims(aud=[CLIENT_ID, "account"], azp=CLIENT_ID))
    assert rig.complete(token).subject == "U-KC-7"


@pytest.mark.parametrize("status", [400, 401, 403])
def test_provider_rejection_is_an_identity_error(status: int) -> None:
    rig = Rig()
    rig.provider.token_status = status
    rig.provider.token_body = json.dumps(
        {"error": "invalid_grant", "access_token": ACCESS}
    ).encode()
    with pytest.raises(IdentityProviderError) as caught:
        rig.complete("x")
    assert ACCESS not in repr(caught.value) + str(caught.value)


@pytest.mark.parametrize("status", [500, 502, 503])
def test_provider_server_errors_are_unavailable(status: int) -> None:
    rig = Rig()
    rig.provider.token_status = status
    with pytest.raises(IdentityProviderUnavailable):
        rig.complete("x")


@pytest.mark.parametrize(
    "error", [httpx.ConnectError("down"), httpx.ReadTimeout("slow")]
)
def test_network_failures_are_unavailable(error: Exception) -> None:
    rig = Rig()
    rig.provider.error = error
    with pytest.raises(IdentityProviderUnavailable):
        rig.complete(sign(claims()))


def test_jwks_outage_is_unavailable_and_bad_token_response_is_an_error() -> None:
    rig = Rig()
    rig.provider.keys_status = 500
    with pytest.raises(IdentityProviderUnavailable):
        rig.complete(sign(claims()))
    rig = Rig()
    rig.provider.token_body = b"<html>not json</html>"
    with pytest.raises(IdentityProviderError):
        rig.complete("x")
    rig.provider.token_body = json.dumps({"access_token": ACCESS}).encode()
    with pytest.raises(IdentityProviderError):
        rig.complete("x")


def test_provider_tokens_do_not_escape_the_adapter() -> None:
    rig = Rig()
    token = sign(claims())
    identity = rig.complete(token)
    exposed = repr(identity) + repr(vars(identity))
    for secret in (token, ACCESS, REFRESH, ID_TOKEN_MARKER):
        assert secret not in exposed
        assert secret not in repr(vars(rig.adapter))
    assert type(identity) is AuthenticatedIdentity
    assert not hasattr(identity, "id_token")


def test_full_login_through_the_app_uses_the_oidc_adapter() -> None:
    rig = Rig()
    session_store = InMemorySessionStore()
    manager = SessionManager(session_store)
    login = LoginService(rig.adapter, InMemoryLoginStore(), manager)
    app = create_app(manager, cookie=CookieSettings(same_site="lax"), login=login)
    browser = TestClient(app, base_url="https://cc.invalid", follow_redirects=False)

    start = browser.get("/v1/session/login")
    assert start.status_code == 302
    location = urlparse(start.headers["location"])
    assert location.path == "/realms/cap/protocol/openid-connect/auth"
    params = {k: v[0] for k, v in parse_qs(location.query).items()}

    # The provider signs a token bound to the nonce it was given, then the
    # browser comes back with a code. PKCE: the verifier must match the challenge.
    rig.provider.id_token = sign(claims(nonce=params["nonce"]))
    done = browser.get(f"/v1/session/callback?code=CODE-1&state={params['state']}")
    assert done.status_code == 302
    verifier = rig.provider.token_requests[0]["code_verifier"][0]
    assert pkce_challenge(verifier) == params["code_challenge"]

    me = browser.get("/v1/session")
    assert me.status_code == 200
    validator_for("session.schema.json").validate(me.json())
    assert me.json()["actor"]["actor_id"] == "U-KC-7"
    assert me.json()["actor"]["roles"] == ["auditor", "ops-controller"]
    everything = (
        start.text + str(start.headers) + done.text + str(done.headers) + me.text
    )
    for secret in (rig.provider.id_token, ACCESS, REFRESH, SECRET):
        assert secret not in everything
        assert secret not in repr(session_store._records)  # pyright: ignore[reportPrivateUsage]


def test_provider_outage_at_start_gives_503_and_leaves_nothing_pending() -> None:
    rig = Rig()
    rig.provider.discovery_status = 503
    manager = SessionManager(InMemorySessionStore())
    store = InMemoryLoginStore()
    app = create_app(
        manager,
        cookie=CookieSettings(same_site="lax"),
        login=LoginService(rig.adapter, store, manager),
    )
    browser = TestClient(app, base_url="https://cc.invalid", follow_redirects=False)
    response = browser.get("/v1/session/login")
    assert response.status_code == 503
    assert response.json()["category"] == "DEPENDENCY_UNAVAILABLE"
    assert store.count() == 0
    assert "set-cookie" not in response.headers
