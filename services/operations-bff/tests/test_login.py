"""OIDC login skeleton behind a deterministic fake identity provider."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from operations_bff.api import create_app
from operations_bff.config import (
    COOKIE_NAME,
    LOGIN_COOKIE_NAME,
    CookieSettings,
    LoginConfig,
)
from operations_bff.errors import Unauthorized
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
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
)
from test_contract_v1 import BASE, operations, registry, validator_for

T0 = datetime(2026, 10, 23, 8, 0, 0, tzinfo=UTC)
SRC = Path(__file__).resolve().parents[1] / "src" / "operations_bff"
IDP_IDENTITY = AuthenticatedIdentity(
    subject="U-IDP-42",
    display_name="IdP Operator",
    roles=("quality-engineer",),
    environment_id="ENV-SYNTHETIC-TEST",
)
PROVIDER_SECRETS = ("FAKE-ACCESS-TOKEN-1", "FAKE-REFRESH-TOKEN-2", "FAKE-ID-TOKEN-3")


class FakeIdP:
    """Holds provider tokens internally and, like the port, returns only identity."""

    def __init__(self) -> None:
        self.requests: list[AuthorizationRequest] = []
        self.completed: list[str] = []
        self.codes: dict[str, tuple[str, str]] = {}
        self.result: Any = IDP_IDENTITY
        self._tokens = PROVIDER_SECRETS

    def authorization_url(self, request: AuthorizationRequest) -> str:
        self.requests.append(request)
        return (
            "https://idp.invalid/authorize"
            f"?state={request.state}&code_challenge={request.code_challenge}"
            f"&code_challenge_method={request.code_challenge_method}"
            f"&nonce={request.nonce}"
        )

    def issue_code(self, code: str = "good-code") -> str:
        last = self.requests[-1]
        self.codes[code] = (last.code_challenge, last.nonce)
        return code

    def complete(
        self, *, code: str, code_verifier: str, nonce: str
    ) -> AuthenticatedIdentity:
        self.completed.append(code)
        if code == "down-code":
            raise IdentityProviderUnavailable
        challenge, expected_nonce = self.codes.get(code, ("", ""))
        if pkce_challenge(code_verifier) != challenge or nonce != expected_nonce:
            raise IdentityProviderError
        return self.result


class Rig:
    def __init__(
        self, *, login_config: LoginConfig | None = None, same_site: Any = "lax"
    ) -> None:
        self.now = T0
        self.idp = FakeIdP()
        self.session_store = InMemorySessionStore()
        self.login_store = InMemoryLoginStore()
        self.manager = SessionManager(self.session_store)
        self.login = LoginService(
            self.idp, self.login_store, self.manager, login_config
        )
        self.app = create_app(
            self.manager,
            cookie=CookieSettings(same_site=same_site),
            clock=lambda: self.now,
            login=self.login,
        )
        self.client = TestClient(
            self.app, base_url="https://testserver", follow_redirects=False
        )

    def start(self) -> dict[str, str]:
        response = self.client.get("/v1/session/login")
        assert response.status_code == 302
        query = parse_qs(urlparse(response.headers["location"]).query)
        return {k: v[0] for k, v in query.items()}

    def callback(self, code: str, state: str, extra: str = "") -> Any:
        return self.client.get(f"/v1/session/callback?code={code}&state={state}{extra}")

    def logged_in(self) -> Any:
        params = self.start()
        code = self.idp.issue_code()
        return self.callback(code, params["state"])


def envelope_validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": BASE + f"common.schema.json#/$defs/{name}"}, registry=registry()
    )


def cookies_of(response: Any) -> dict[str, str]:
    return {
        header.split("=", 1)[0]: header
        for header in response.headers.get_list("set-cookie")
    }


def test_pkce_challenge_matches_the_rfc_7636_vector() -> None:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert pkce_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"


def test_start_login_creates_state_pkce_and_binding_cookie() -> None:
    rig = Rig()
    response = rig.client.get("/v1/session/login")
    assert response.status_code == 302
    assert response.headers["cache-control"] == "no-store"
    assert response.content == b""
    location = urlparse(response.headers["location"])
    assert location.netloc == "idp.invalid"
    query = {k: v[0] for k, v in parse_qs(location.query).items()}
    assert query["code_challenge_method"] == "S256"
    assert len(query["state"]) >= 43
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", query["code_challenge"])
    request = rig.idp.requests[-1]
    assert (request.state, request.nonce) == (query["state"], query["nonce"])
    cookie = cookies_of(response)[LOGIN_COOKIE_NAME].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert "path=/v1/session" in cookie
    assert "max-age=600" in cookie
    # Only the server holds the verifier; it is not in anything the browser got.
    assert rig.login_store.count() == 1
    verifier = next(iter(rig.login_store._items.values())).code_verifier  # pyright: ignore[reportPrivateUsage]
    assert verifier not in response.headers["location"]
    assert verifier not in str(response.headers)
    assert pkce_challenge(verifier) == query["code_challenge"]
    assert rig.start()["state"] != query["state"]


def test_pending_logins_are_bounded() -> None:
    rig = Rig(login_config=LoginConfig(max_pending=2))
    rig.start()
    rig.start()
    response = rig.client.get("/v1/session/login")
    assert response.status_code == 503
    body = response.json()
    envelope_validator("ErrorEnvelope").validate(body)
    assert body["category"] == "DEPENDENCY_UNAVAILABLE"
    rig.now = T0 + rig.login.config.ttl
    assert rig.client.get("/v1/session/login").status_code == 302


def test_successful_callback_establishes_session_and_cookie() -> None:
    rig = Rig(same_site="strict")
    response = rig.logged_in()
    assert response.status_code == 302
    assert response.headers["location"] == "/"
    assert response.content == b""
    cookies = cookies_of(response)
    session_cookie = cookies[COOKIE_NAME]
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert "samesite=strict" in session_cookie.lower()
    assert (
        f"Max-Age={int(rig.manager.config.absolute_ttl.total_seconds())}"
        in session_cookie
    )
    assert "Max-Age=0" in cookies[LOGIN_COOKIE_NAME]
    assert rig.idp.completed == ["good-code"]
    # The new session works and the actor is the provider-validated identity.
    me = rig.client.get("/v1/session")
    assert me.status_code == 200
    validator_for("session.schema.json").validate(me.json())
    assert me.json()["actor"] == {
        "actor_id": "U-IDP-42",
        "display_name": "IdP Operator",
        "roles": ["quality-engineer"],
        "derived_from": "SESSION",
    }


@pytest.mark.parametrize(
    "case", ["unknown_state", "replay", "expired", "no_binding", "other_binding"]
)
def test_bad_login_transactions_are_rejected_without_a_session(case: str) -> None:
    rig = Rig()
    params = rig.start()
    code = rig.idp.issue_code()
    state = params["state"]
    if case == "unknown_state":
        state = "x" * 43
    elif case == "replay":
        assert rig.callback(code, state).status_code == 302
        rig.client.cookies.clear()
        rig.client.cookies.set(LOGIN_COOKIE_NAME, "anything", path="/v1/session")
        rig.idp.completed.clear()
    elif case == "expired":
        rig.now = T0 + rig.login.config.ttl
    elif case == "no_binding":
        rig.client.cookies.clear()
    else:
        rig.client.cookies.clear()
        rig.client.cookies.set(LOGIN_COOKIE_NAME, "attacker", path="/v1/session")
    before = len(rig.session_store._records)  # pyright: ignore[reportPrivateUsage]
    response = rig.callback(code, state)
    assert response.status_code == 401
    envelope_validator("UnauthorizedError").validate(response.json())
    assert response.json()["error_code"] == "LOGIN_REJECTED"
    assert COOKIE_NAME not in cookies_of(response)
    assert "Max-Age=0" in cookies_of(response)[LOGIN_COOKIE_NAME]
    assert len(rig.session_store._records) == before  # pyright: ignore[reportPrivateUsage]
    assert rig.idp.completed == []  # the provider is never asked


def test_a_failed_attempt_spends_the_transaction() -> None:
    rig = Rig()
    params = rig.start()
    code = rig.idp.issue_code()
    saved = rig.client.cookies.get(LOGIN_COOKIE_NAME, path="/v1/session")
    rig.client.cookies.clear()
    assert rig.callback(code, params["state"]).status_code == 401
    rig.client.cookies.set(LOGIN_COOKIE_NAME, saved or "", path="/v1/session")
    assert rig.callback(code, params["state"]).status_code == 401
    assert rig.idp.completed == []


def test_code_verifier_and_nonce_must_match_what_was_started() -> None:
    rig = Rig()
    params = rig.start()
    rig.idp.codes["good-code"] = ("someone-elses-challenge", rig.idp.requests[-1].nonce)
    response = rig.callback("good-code", params["state"])
    assert response.status_code == 401
    assert rig.idp.completed == ["good-code"]
    assert rig.client.get("/v1/session").status_code == 401


@pytest.mark.parametrize(
    "code,status,category",
    [
        ("unissued-code", 401, "UNAUTHORIZED"),
        ("down-code", 503, "DEPENDENCY_UNAVAILABLE"),
    ],
)
def test_provider_failure_creates_no_session(
    code: str, status: int, category: str
) -> None:
    rig = Rig()
    params = rig.start()
    response = rig.callback(code, params["state"])
    assert response.status_code == status
    assert response.json()["category"] == category
    assert COOKIE_NAME not in cookies_of(response)
    assert rig.client.get("/v1/session").status_code == 401
    assert len(rig.session_store._records) == 0  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    "result",
    [
        {"subject": "U-1", "roles": []},
        None,
        AuthenticatedIdentity(" ", "Name", ("r",), "ENV"),
        AuthenticatedIdentity("U-1", "Name", ("",), "ENV"),
        AuthenticatedIdentity("U-1", "Name", ("r",), ""),
    ],
)
def test_only_a_validated_identity_result_is_accepted(result: Any) -> None:
    rig = Rig()
    rig.idp.result = result
    params = rig.start()
    response = rig.callback(rig.idp.issue_code(), params["state"])
    assert response.status_code == 401
    assert len(rig.session_store._records) == 0  # pyright: ignore[reportPrivateUsage]


def test_provider_tokens_never_reach_the_browser_or_stores() -> None:
    rig = Rig()
    start = rig.client.get("/v1/session/login")
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    done = rig.callback(rig.idp.issue_code(), state)
    me = rig.client.get("/v1/session")
    outputs = "".join(
        [start.text, str(start.headers), done.text, str(done.headers), me.text]
        + [str(c) for c in rig.client.cookies.jar]
    )
    stored = repr(rig.session_store._records) + repr(rig.login_store._items)  # pyright: ignore[reportPrivateUsage]
    for secret in PROVIDER_SECRETS:
        assert secret not in outputs
        assert secret not in stored
    assert "idp.invalid" not in done.headers["location"]
    assert done.headers["location"] == "/"


def test_login_rotates_and_ends_a_previous_session() -> None:
    rig = Rig()
    assert rig.logged_in().status_code == 302
    old = rig.client.cookies.get(COOKIE_NAME)
    assert old
    params = rig.start()
    response = rig.callback(rig.idp.issue_code("second-code"), params["state"])
    assert response.status_code == 302
    new = rig.client.cookies.get(COOKIE_NAME)
    assert new and new != old
    with pytest.raises(Unauthorized):
        rig.manager.resolve(old, T0)


def test_browser_cannot_influence_the_resulting_actor() -> None:
    rig = Rig()
    params = rig.start()
    code = rig.idp.issue_code()
    response = rig.callback(code, params["state"], "&actor_id=U-ADMIN&roles=admin")
    assert response.status_code == 302
    forged = rig.client.get("/v1/session", headers={"X-Actor": "U-ADMIN"})
    assert forged.status_code == 400
    ok = rig.client.get("/v1/session?actor_id=U-ADMIN")
    assert ok.json()["actor"]["actor_id"] == "U-IDP-42"


@pytest.mark.parametrize(
    "query",
    ["", "?code=c", "?state=s", "?code=&state=s", "?code=c&state=" + "s" * 3000],
)
def test_callback_parameters_are_validated_with_400(query: str) -> None:
    rig = Rig()
    response = rig.client.get("/v1/session/callback" + query)
    assert response.status_code == 400
    body = response.json()
    envelope_validator("ErrorEnvelope").validate(body)
    assert body["category"] == "VALIDATION_ERROR"
    assert "sss" not in response.text


def test_post_login_redirect_must_be_a_same_origin_path() -> None:
    rig = Rig()
    for bad in ("//evil.example", "https://evil.example/", "relative", ""):
        with pytest.raises(ValueError):
            create_app(
                rig.manager,
                cookie=CookieSettings(same_site="lax"),
                login=rig.login,
                post_login_redirect=bad,
            )


def test_login_config_is_bounded() -> None:
    for ttl in (timedelta(minutes=16), timedelta(0)):
        with pytest.raises(ValueError):
            LoginConfig(ttl=ttl)
    with pytest.raises(ValueError):
        LoginConfig(max_pending=0)


def test_login_routes_match_the_anonymous_contract_operations() -> None:
    rig = Rig()
    wired = {
        r.operation_id: (r.path, r.methods)  # type: ignore[attr-defined]
        for r in rig.app.routes
        if getattr(r, "operation_id", None)
    }
    assert set(wired) == {"getSession", "logout", "startLogin", "completeLogin"}
    contract = operations()
    for name in ("startLogin", "completeLogin"):
        path, method, op = contract[name]
        assert wired[name] == (path, {method.upper()})
        assert op["security"] == []
    headers = contract["startLogin"][2]["responses"]["302"]["headers"]
    assert {"Location", "Set-Cookie"} <= set(headers)


def test_no_provider_urls_or_secrets_are_hard_coded_in_the_runtime() -> None:
    for path in SRC.glob("*.py"):
        text = path.read_text()
        assert not re.search(r"https?://[A-Za-z0-9]", text), path.name
        if path.name != "oidc.py":
            lowered = text.lower()
            for word in ("keycloak", "client_secret", "realm"):
                assert word not in lowered, (path.name, word)
