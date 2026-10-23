"""FastAPI transport adapter: HTTP behaviour of getSession and logout."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from operations_bff.api import (
    clear_session_cookie,
    create_app,
    write_session_cookie,
)
from operations_bff.config import COOKIE_NAME, CSRF_HEADER, CookieSettings
from operations_bff.errors import Unauthorized
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
    SessionRecord,
    session_view,
)
from test_contract_v1 import BASE, openapi, operations, registry, validator_for

T0 = datetime(2026, 10, 23, 8, 0, 0, tzinfo=UTC)
IDENTITY = AuthenticatedIdentity(
    subject="U-SYNTHETIC-01",
    display_name="Synthetic Operator",
    roles=("ops-controller",),
    environment_id="ENV-SYNTHETIC-TEST",
)
SRC = Path(__file__).resolve().parents[1] / "src" / "operations_bff"


class Clock:
    def __init__(self) -> None:
        self.now = T0

    def __call__(self) -> datetime:
        return self.now


class Rig:
    def __init__(self, same_site: Literal["strict", "lax"] = "lax") -> None:
        self.clock = Clock()
        self.manager = SessionManager(InMemorySessionStore())
        self.cookie = CookieSettings(same_site=same_site)
        self.app = create_app(self.manager, cookie=self.cookie, clock=self.clock)
        self.client = TestClient(self.app, base_url="https://testserver")

    def login(self) -> SessionRecord:
        record = self.manager.create(IDENTITY, self.clock.now)
        self.client.cookies.set(COOKIE_NAME, record.session_id)
        return record


def envelope_validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": BASE + f"common.schema.json#/$defs/{name}"}, registry=registry()
    )


def test_valid_session_returns_contract_valid_response() -> None:
    rig = Rig()
    record = rig.login()
    response = rig.client.get("/v1/session")
    assert response.status_code == 200
    body = response.json()
    validator_for("session.schema.json").validate(body)
    assert body == session_view(record)
    assert response.headers["cache-control"] == "no-store"
    assert "set-cookie" not in response.headers
    assert record.session_id not in response.text


@pytest.mark.parametrize("case", ["missing", "unknown", "idle_expired", "abs_expired"])
def test_missing_or_expired_session_is_401(case: str) -> None:
    rig = Rig()
    record = rig.login()
    if case == "missing":
        rig.client.cookies.clear()
    elif case == "unknown":
        rig.client.cookies.set(COOKIE_NAME, "not-a-session")
    elif case == "idle_expired":
        rig.clock.now = T0 + rig.manager.config.idle_ttl
    else:
        rig.clock.now = record.expires_at
    response = rig.client.get("/v1/session")
    assert response.status_code == 401
    envelope_validator("UnauthorizedError").validate(response.json())
    assert "set-cookie" not in response.headers


def test_logout_requires_valid_csrf() -> None:
    rig = Rig()
    record = rig.login()
    for headers in ({}, {CSRF_HEADER: ""}, {CSRF_HEADER: "wrong"}):
        response = rig.client.post("/v1/session/logout", headers=headers)
        assert response.status_code == 403
        envelope_validator("ForbiddenError").validate(response.json())
        assert "set-cookie" not in response.headers
    # The refused attempts left the session intact.
    assert rig.client.get("/v1/session").status_code == 200
    ok = rig.client.post("/v1/session/logout", headers={CSRF_HEADER: record.csrf_token})
    assert ok.status_code == 204


def test_anonymous_logout_is_401_not_403() -> None:
    rig = Rig()
    response = rig.client.post("/v1/session/logout", headers={CSRF_HEADER: "x"})
    assert response.status_code == 401
    envelope_validator("UnauthorizedError").validate(response.json())


@pytest.mark.parametrize("same_site", ["strict", "lax"])
def test_logout_invalidates_server_side_and_clears_cookie(
    same_site: Literal["strict", "lax"],
) -> None:
    rig = Rig(same_site)
    record = rig.login()
    response = rig.client.post(
        "/v1/session/logout", headers={CSRF_HEADER: record.csrf_token}
    )
    assert response.status_code == 204
    assert response.content == b""
    cleared = response.headers["set-cookie"]
    assert cleared.startswith(f"{COOKIE_NAME}=")
    assert re.search(r"Max-Age=0", cleared, re.IGNORECASE)
    assert "HttpOnly" in cleared
    assert "Secure" in cleared
    assert f"samesite={same_site}" in cleared.lower()
    # Server side: even a client that kept the old cookie value is refused.
    replay = TestClient(rig.app, base_url="https://testserver")
    replay.cookies.set(COOKIE_NAME, record.session_id)
    assert replay.get("/v1/session").status_code == 401
    with pytest.raises(Unauthorized):
        rig.manager.resolve(record.session_id, rig.clock.now)


def test_actor_comes_only_from_the_server_session() -> None:
    rig = Rig()
    rig.login()
    forged = {"X-Actor": "U-ADMIN", "X-User-Id": "U-ADMIN", "X-Roles": "admin"}
    for name, value in forged.items():
        response = rig.client.get("/v1/session", headers={name: value})
        assert response.status_code == 400
        envelope_validator("ErrorEnvelope").validate(response.json())
        assert response.json()["category"] == "VALIDATION_ERROR"
    response = rig.client.get("/v1/session?actor_id=U-ADMIN&roles=admin")
    assert response.status_code == 200
    assert response.json()["actor"]["actor_id"] == IDENTITY.subject
    assert response.json()["actor"]["roles"] == ["ops-controller"]
    assert response.json()["actor"]["derived_from"] == "SESSION"


def test_error_envelopes_carry_server_generated_correlation_ids() -> None:
    rig = Rig()
    first = rig.client.get("/v1/session").json()["correlation_id"]
    second = rig.client.get("/v1/session", headers={"X-Correlation-Id": "mine"}).json()
    assert first != second["correlation_id"]
    assert second["correlation_id"] != "mine"


@pytest.mark.parametrize("same_site", ["strict", "lax"])
def test_written_cookie_has_required_security_attributes(
    same_site: Literal["strict", "lax"],
) -> None:
    rig = Rig(same_site)
    record = rig.manager.create(IDENTITY, T0)
    response = Response()
    write_session_cookie(response, record, rig.cookie, T0 + timedelta(minutes=10))
    header = response.headers["set-cookie"]
    parts = {p.strip().split("=")[0].lower(): p for p in header.split(";")}
    assert header.startswith(f"{COOKIE_NAME}={record.session_id}")
    assert "httponly" in parts
    assert "secure" in parts
    assert parts["samesite"].split("=")[1].lower() == same_site
    assert parts["path"].split("=")[1] == "/"
    expected = int((record.expires_at - T0 - timedelta(minutes=10)).total_seconds())
    assert int(parts["max-age"].split("=")[1]) == expected
    assert expected <= rig.manager.config.absolute_ttl.total_seconds()
    assert IDENTITY.subject not in header
    cleared = Response()
    clear_session_cookie(cleared, rig.cookie)
    assert "httponly" in cleared.headers["set-cookie"].lower()
    assert "secure" in cleared.headers["set-cookie"].lower()


def test_cookie_policy_is_configuration_and_never_allows_none() -> None:
    with pytest.raises(TypeError):
        CookieSettings()  # type: ignore[call-arg]
    for bad in ("none", "None", "", "strictish"):
        with pytest.raises(ValueError):
            CookieSettings(same_site=bad)  # type: ignore[arg-type]
    assert not {"secure", "http_only", "httponly"} & set(CookieSettings.__annotations__)
    contract = openapi()["components"]["securitySchemes"]["browserSession"]
    allowed = contract["x-cookie-attributes"]["same_site_one_of"]
    assert {v.lower() for v in allowed} == {"strict", "lax"}


def test_only_the_wired_contract_operations_are_exposed() -> None:
    rig = Rig()
    wired: dict[str, tuple[str, set[str]]] = {}
    for route in rig.app.routes:
        operation_id = getattr(route, "operation_id", None)
        if operation_id:
            wired[operation_id] = (route.path, route.methods)  # type: ignore[attr-defined]
    assert set(wired) == {"getSession", "logout"}
    contract = operations()
    for operation_id, (path, methods) in wired.items():
        contract_path, contract_method, _ = contract[operation_id]
        assert path == contract_path
        assert methods == {contract_method.upper()}
    assert contract["logout"][2]["responses"]["204"]
    for missing in ("/openapi.json", "/docs", "/redoc", "/v1/session/login"):
        assert rig.client.get(missing).status_code == 404


def test_fastapi_is_confined_to_the_transport_module() -> None:
    importers = {
        path.name
        for path in SRC.glob("*.py")
        if re.search(r"^\s*(from|import)\s+(fastapi|starlette)", path.read_text(), re.M)
    }
    # The composition root and entrypoint name the app type; domain modules never do.
    assert importers == {"api.py", "composition.py", "main.py"}
    for path in SRC.glob("*.py"):
        text = path.read_text()
        assert not re.search(
            r"^\s*(from|import)\s+(nats|psycopg|sqlalchemy)", text, re.M
        )
