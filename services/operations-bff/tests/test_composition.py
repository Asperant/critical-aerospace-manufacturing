"""Composition root: configuration, wiring and boundaries."""

from __future__ import annotations

import re
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
import test_oidc as oidc_helpers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from operations_bff.composition import (
    ConfigurationError,
    RuntimeSettings,
    build_app,
)
from operations_bff.main import create_app
from test_contract_v1 import validator_for

SRC = Path(__file__).resolve().parents[1] / "src"
PKG = SRC / "operations_bff"
ENV = {
    "OPERATIONS_BFF_OIDC_ISSUER": oidc_helpers.ISSUER,
    "OPERATIONS_BFF_OIDC_CLIENT_ID": oidc_helpers.CLIENT_ID,
    "OPERATIONS_BFF_OIDC_REDIRECT_URI": oidc_helpers.REDIRECT,
    "OPERATIONS_BFF_OIDC_ENVIRONMENT_ID": "ENV-SYNTHETIC-TEST",
    "OPERATIONS_BFF_OIDC_CLIENT_SECRET": oidc_helpers.SECRET,
    "OPERATIONS_BFF_COOKIE_SAMESITE": "lax",
    "OPERATIONS_BFF_SESSION_ABSOLUTE_TTL_SECONDS": "28800",
    "OPERATIONS_BFF_SESSION_IDLE_TTL_SECONDS": "1800",
    "OPERATIONS_BFF_SESSION_ROTATE_AFTER_SECONDS": "900",
}
REQUIRED = [
    "OPERATIONS_BFF_OIDC_ISSUER",
    "OPERATIONS_BFF_OIDC_CLIENT_ID",
    "OPERATIONS_BFF_OIDC_REDIRECT_URI",
    "OPERATIONS_BFF_OIDC_ENVIRONMENT_ID",
    "OPERATIONS_BFF_COOKIE_SAMESITE",
    "OPERATIONS_BFF_SESSION_ABSOLUTE_TTL_SECONDS",
    "OPERATIONS_BFF_SESSION_IDLE_TTL_SECONDS",
    "OPERATIONS_BFF_SESSION_ROTATE_AFTER_SECONDS",
]


def env(**overrides: str | None) -> dict[str, str]:
    merged: dict[str, str | None] = {**ENV, **overrides}
    return {k: v for k, v in merged.items() if v is not None}


def wired(
    environ: dict[str, str] | None = None,
) -> tuple[FastAPI, oidc_helpers.Provider]:
    provider = oidc_helpers.Provider()
    client = httpx.Client(transport=httpx.MockTransport(provider.handle))
    settings = RuntimeSettings.from_environ(environ or env())
    return build_app(settings, http_client=client), provider


def test_valid_environment_builds_settings_and_an_app() -> None:
    settings = RuntimeSettings.from_environ(env())
    assert settings.cookie.same_site == "lax"
    assert settings.session.absolute_ttl == timedelta(hours=8)
    assert settings.session.idle_ttl == timedelta(minutes=30)
    assert settings.session.rotate_after == timedelta(minutes=15)
    assert settings.login.max_pending == 1000
    assert settings.post_login_path == "/"
    assert settings.oidc.client_secret == oidc_helpers.SECRET
    assert oidc_helpers.SECRET not in repr(settings)
    app, provider = wired()
    assert isinstance(app, FastAPI)
    assert provider.calls == []  # building never contacts the provider


@pytest.mark.parametrize("name", REQUIRED)
def test_each_required_setting_fails_fast_by_name(name: str) -> None:
    with pytest.raises(ConfigurationError) as caught:
        RuntimeSettings.from_environ(env(**{name: None}))
    assert any(name in problem for problem in caught.value.problems)
    with pytest.raises(ConfigurationError):
        RuntimeSettings.from_environ(env(**{name: "  "}))


def test_empty_environment_lists_every_problem_and_has_no_defaults() -> None:
    with pytest.raises(ConfigurationError) as caught:
        RuntimeSettings.from_environ({})
    text = str(caught.value)
    for name in REQUIRED:
        assert name in text


@pytest.mark.parametrize(
    "overrides",
    [
        {"OPERATIONS_BFF_COOKIE_SAMESITE": "none"},
        {"OPERATIONS_BFF_COOKIE_SAMESITE": "Lax"},
        {"OPERATIONS_BFF_SESSION_ABSOLUTE_TTL_SECONDS": "eight"},
        {"OPERATIONS_BFF_SESSION_ABSOLUTE_TTL_SECONDS": "-5"},
        {"OPERATIONS_BFF_SESSION_ABSOLUTE_TTL_SECONDS": "0"},
        {"OPERATIONS_BFF_SESSION_ABSOLUTE_TTL_SECONDS": "86400"},
        {"OPERATIONS_BFF_SESSION_IDLE_TTL_SECONDS": "30000"},
        {"OPERATIONS_BFF_SESSION_ROTATE_AFTER_SECONDS": "3600"},
        {"OPERATIONS_BFF_LOGIN_TTL_SECONDS": "7200"},
        {"OPERATIONS_BFF_LOGIN_MAX_PENDING": "0"},
        {"OPERATIONS_BFF_LOGIN_MAX_PENDING": "many"},
        {"OPERATIONS_BFF_POST_LOGIN_PATH": "//evil.example"},
        {"OPERATIONS_BFF_POST_LOGIN_PATH": "https://evil.example/"},
        {"OPERATIONS_BFF_OIDC_ISSUER": "http://idp.invalid/realms/cap"},
        {"OPERATIONS_BFF_OIDC_REDIRECT_URI": "https://cc.invalid/elsewhere"},
        {"OPERATIONS_BFF_OIDC_ALGORITHMS": "HS256"},
    ],
)
def test_invalid_values_fail_explicitly_without_leaking_the_secret(
    overrides: dict[str, str],
) -> None:
    with pytest.raises(ConfigurationError) as caught:
        RuntimeSettings.from_environ(env(**overrides))
    assert str(caught.value).startswith("invalid configuration:")
    assert oidc_helpers.SECRET not in str(caught.value)


def test_optional_settings_are_applied_when_present() -> None:
    settings = RuntimeSettings.from_environ(
        env(
            OPERATIONS_BFF_LOGIN_TTL_SECONDS="120",
            OPERATIONS_BFF_LOGIN_MAX_PENDING="7",
            OPERATIONS_BFF_POST_LOGIN_PATH="/overview",
            OPERATIONS_BFF_COOKIE_SAMESITE="strict",
        )
    )
    assert settings.login.ttl == timedelta(seconds=120)
    assert settings.login.max_pending == 7
    assert settings.post_login_path == "/overview"
    assert settings.cookie.same_site == "strict"


def test_entrypoint_fails_fast_and_builds_from_the_process_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ENV:
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ConfigurationError):
        create_app()
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    assert isinstance(create_app(), FastAPI)


def test_routes_are_registered_exactly_once() -> None:
    app, _ = wired()
    seen: list[tuple[str, frozenset[str]]] = []
    for route in app.routes:
        operation_id = getattr(route, "operation_id", None)
        if operation_id:
            seen.append((operation_id, frozenset(route.methods)))  # type: ignore[attr-defined]
    assert sorted(op for op, _ in seen) == [
        "completeLogin",
        "getSession",
        "logout",
        "startLogin",
    ]
    paths = [r.path for r in app.routes if getattr(r, "operation_id", None)]  # type: ignore[attr-defined]
    assert len(paths) == len(set(paths)) == 4


@pytest.mark.parametrize("same_site", ["strict", "lax"])
def test_wired_flow_keeps_the_security_behaviour(same_site: str) -> None:
    app, provider = wired(env(OPERATIONS_BFF_COOKIE_SAMESITE=same_site))
    browser = TestClient(app, base_url="https://cc.invalid", follow_redirects=False)

    assert browser.get("/v1/session").status_code == 401
    start = browser.get("/v1/session/login")
    assert start.status_code == 302
    params = {
        k: v[0] for k, v in parse_qs(urlparse(start.headers["location"]).query).items()
    }
    assert params["code_challenge_method"] == "S256"

    provider.id_token = oidc_helpers.sign(oidc_helpers.claims(nonce=params["nonce"]))
    done = browser.get(f"/v1/session/callback?code=CODE-1&state={params['state']}")
    assert done.status_code == 302
    cookies = {h.split("=", 1)[0]: h for h in done.headers.get_list("set-cookie")}
    session_cookie = cookies["cap_session"]
    assert "HttpOnly" in session_cookie
    assert "Secure" in session_cookie
    assert f"samesite={same_site}" in session_cookie.lower()
    assert "Max-Age=28800" in session_cookie  # the configured absolute lifetime

    me = browser.get("/v1/session")
    assert me.status_code == 200
    validator_for("session.schema.json").validate(me.json())
    body = me.json()
    assert body["actor"]["actor_id"] == "U-KC-7"
    forged = browser.get("/v1/session", headers={"X-Actor": "U-ADMIN"})
    assert forged.status_code == 400

    # CSRF: logout without the token is refused, with it the session ends.
    assert browser.post("/v1/session/logout").status_code == 403
    out = browser.post(
        "/v1/session/logout", headers={"X-CSRF-Token": body["csrf_token"]}
    )
    assert out.status_code == 204
    assert browser.get("/v1/session").status_code == 401

    seen = start.text + str(start.headers) + done.text + str(done.headers) + me.text
    for secret in (provider.id_token, oidc_helpers.ACCESS, oidc_helpers.REFRESH):
        assert secret not in seen
    assert oidc_helpers.SECRET not in seen


def test_demo_dynamic_redirect_is_exactly_bound_to_the_request_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPERATIONS_BFF_OIDC_DYNAMIC_REDIRECT", "1")
    app, provider = wired(
        env(
            OPERATIONS_BFF_OIDC_DYNAMIC_REDIRECT="1",
            OPERATIONS_BFF_OIDC_ALLOW_INSECURE_HTTP="1",
            OPERATIONS_BFF_OIDC_REDIRECT_URI=(
                "http://localhost:29090/v1/session/callback"
            ),
            OPERATIONS_BFF_OIDC_REDIRECT_URIS=(
                "https://ailab.taila9669.ts.net/v1/session/callback"
            ),
            OPERATIONS_BFF_OIDC_BROWSER_ISSUER="http://localhost:28090/realms/cap",
            OPERATIONS_BFF_OIDC_BROWSER_ISSUERS=(
                "https://ailab.taila9669.ts.net:9443/realms/cap"
            ),
        )
    )
    local = TestClient(app, base_url="http://localhost:29090", follow_redirects=False)
    public = TestClient(
        app, base_url="https://ailab.taila9669.ts.net", follow_redirects=False
    )

    local_start = local.get("/v1/session/login")
    public_start = public.get("/v1/session/login")
    assert local_start.status_code == public_start.status_code == 302
    local_query = parse_qs(urlparse(local_start.headers["location"]).query)
    public_query = parse_qs(urlparse(public_start.headers["location"]).query)
    assert local_query["redirect_uri"] == ["http://localhost:29090/v1/session/callback"]
    assert public_query["redirect_uri"] == [
        "https://ailab.taila9669.ts.net/v1/session/callback"
    ]
    assert local_start.headers["location"].startswith(
        "http://localhost:28090/realms/cap/"
    )
    assert public_start.headers["location"].startswith(
        "https://ailab.taila9669.ts.net:9443/realms/cap/"
    )
    assert provider.calls == ["/realms/cap/.well-known/openid-configuration"]


def test_configured_lifetimes_drive_the_session() -> None:
    provider = oidc_helpers.Provider()
    client = httpx.Client(transport=httpx.MockTransport(provider.handle))
    now = [oidc_helpers.T0]
    settings = RuntimeSettings.from_environ(
        env(
            OPERATIONS_BFF_SESSION_IDLE_TTL_SECONDS="60",
            OPERATIONS_BFF_SESSION_ROTATE_AFTER_SECONDS="30",
        )
    )
    app = build_app(settings, http_client=client, clock=lambda: now[0])
    browser = TestClient(app, base_url="https://cc.invalid", follow_redirects=False)
    start = browser.get("/v1/session/login")
    query = parse_qs(urlparse(start.headers["location"]).query)
    provider.id_token = oidc_helpers.sign(oidc_helpers.claims(nonce=query["nonce"][0]))
    browser.get(f"/v1/session/callback?code=CODE-1&state={query['state'][0]}")
    now[0] += timedelta(seconds=59)
    assert browser.get("/v1/session").status_code == 200
    now[0] += timedelta(seconds=60)  # idle for the configured 60 s
    assert browser.get("/v1/session").status_code == 401


def test_composition_is_the_only_place_that_wires_the_adapter() -> None:
    importers: dict[str, set[str]] = {"oidc": set(), "composition": set()}
    for path in PKG.glob("*.py"):
        text = path.read_text()
        for name in importers:
            if re.search(
                rf"^\s*from\s+\.{name}\s+import|^\s*from\s+operations_bff\.{name}",
                text,
                re.M,
            ):
                importers[name].add(path.name)
    assert importers["oidc"] == {"composition.py"}
    assert importers["composition"] == {"main.py"}
    for path in PKG.glob("*.py"):
        if path.name in {
            "session.py",
            "login.py",
            "actor.py",
            "idp.py",
            "oidc.py",
            "config.py",
            "errors.py",
        }:
            assert not re.search(
                r"^\s*(from|import)\s+(fastapi|starlette)", path.read_text(), re.M
            ), path.name


def test_no_broker_or_database_dependency_is_introduced() -> None:
    banned = (
        "nats",
        "psycopg",
        "sqlalchemy",
        "redis",
        "valkey",
        "kafka",
        "pika",
        "temporalio",
        "boto3",
    )
    for path in PKG.glob("*.py"):
        text = path.read_text()
        for name in banned:
            assert not re.search(rf"^\s*(from|import)\s+{name}\b", text, re.M), (
                path.name,
                name,
            )
    probe = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "import operations_bff.main;"
        f"print(sorted(m for m in sys.modules if m.split('.')[0] in {banned!r}))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", probe, str(SRC)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "[]"


def test_no_default_hides_required_configuration() -> None:
    text = (PKG / "composition.py").read_text()
    assert not re.search(r"environ\.get\([^)]*,\s*[\"'][^\"']+[\"']", text)
    assert "os.environ" not in text  # only the entrypoint reads the process environment
    assert "os.environ" in (PKG / "main.py").read_text()
