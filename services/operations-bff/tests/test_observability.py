"""Structured access logging, correlation propagation and the health surface."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fakes_overview import from_fixture
from fastapi.testclient import TestClient
from operations_bff.api import create_app
from operations_bff.config import COOKIE_NAME, CSRF_HEADER, CookieSettings
from operations_bff.observability import (
    ACCESS_LOGGER,
    CORRELATION_HEADER,
    access_record,
    configure_access_log,
    health_body,
    outcome_of,
)
from operations_bff.overview import OverviewService
from operations_bff.session import (
    AuthenticatedIdentity,
    InMemorySessionStore,
    SessionManager,
)
from test_contract_v1 import operations

NOW = datetime(2026, 10, 23, 9, 0, 5, tzinfo=UTC)
IDENTITY = AuthenticatedIdentity("U-1", "Operator", ("ops-controller",), "ENV-1")


class Rig:
    def __init__(self, *, overview: bool = True) -> None:
        self.core, self.twin, _ = from_fixture()
        self.manager = SessionManager(InMemorySessionStore())
        self.app = create_app(
            self.manager,
            cookie=CookieSettings(same_site="lax"),
            clock=lambda: NOW,
            overview=OverviewService(self.core, [self.twin]) if overview else None,
        )
        self.client = TestClient(
            self.app, base_url="https://testserver", follow_redirects=False
        )
        self.record = self.manager.create(IDENTITY, NOW)
        self.client.cookies.set(COOKIE_NAME, self.record.session_id)


class Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


@pytest.fixture
def caplog() -> Iterator[Capture]:
    """Shadows pytest's fixture: attach directly, independent of propagation."""
    handler = Capture()
    logger = logging.getLogger(ACCESS_LOGGER)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield handler
    logger.removeHandler(handler)


def records(captured: Capture) -> list[dict[str, Any]]:
    return [json.loads(line) for line in captured.lines]


def test_every_request_logs_one_structured_record(
    caplog: Capture,
) -> None:
    rig = Rig()
    ok = rig.client.get("/v1/session")
    denied = rig.client.post("/v1/session/logout")
    missing = rig.client.get("/nowhere?token=SECRET-QUERY")
    logged = records(caplog)
    assert [r["status"] for r in logged] == [200, 403, 404]
    assert [r["outcome"] for r in logged] == ["success", "client_error", "client_error"]
    assert [r["operation_id"] for r in logged] == ["getSession", "logout", None]
    assert [r["route"] for r in logged] == [
        "/v1/session",
        "/v1/session/logout",
        "unmatched",
    ]
    for record, response in zip(logged, (ok, denied, missing), strict=True):
        assert record["event"] == "http_request"
        assert record["service"] == "operations-bff"
        assert isinstance(record["duration_ms"], float) and record["duration_ms"] >= 0
        assert record["correlation_id"] == response.headers[CORRELATION_HEADER]
        assert re.fullmatch(r"[0-9a-f]{32}", record["correlation_id"])
    assert len({r["correlation_id"] for r in logged}) == 3


def test_logs_never_carry_secrets_queries_or_identity(
    caplog: Capture,
) -> None:
    rig = Rig()
    rig.client.get("/v1/overview?world_id=W-SECRET-WORLD")
    rig.client.post("/v1/session/logout", headers={CSRF_HEADER: rig.record.csrf_token})
    text = "\n".join(caplog.lines)
    for secret in (
        rig.record.session_id,
        rig.record.csrf_token,
        "W-SECRET-WORLD",
        "U-1",
        "Operator",
        "cap_session",
    ):
        assert secret not in text


def test_error_envelopes_and_headers_share_the_logged_correlation_id(
    caplog: Capture,
) -> None:
    rig = Rig()
    rig.client.cookies.clear()
    response = rig.client.get("/v1/session", headers={CORRELATION_HEADER: "mine"})
    assert response.status_code == 401
    (record,) = records(caplog)
    assert response.json()["correlation_id"] == record["correlation_id"]
    assert response.headers[CORRELATION_HEADER] == record["correlation_id"]
    assert record["correlation_id"] != "mine"  # never taken from the browser


def test_the_correlation_id_reaches_the_read_ports_and_the_overview_meta() -> None:
    rig = Rig()
    response = rig.client.get("/v1/overview?world_id=W-1")
    assert response.status_code == 200
    expected = response.headers[CORRELATION_HEADER]
    assert response.json()["meta"]["correlation_id"] == expected
    assert [q.correlation_id for q in rig.core.queries] == [expected]
    assert [q.correlation_id for q in rig.twin.queries] == [expected]


def test_a_server_error_is_logged_as_such(caplog: Capture) -> None:
    rig = Rig()
    rig.core.down = True
    assert rig.client.get("/v1/overview?world_id=W-1").status_code == 503
    (record,) = records(caplog)
    assert record["status"] == 503
    assert record["outcome"] == "server_error"
    assert record["operation_id"] == "getManufacturingOverview"


def test_health_surface_needs_no_session_and_makes_no_backend_call() -> None:
    rig = Rig()
    rig.client.cookies.clear()
    response = rig.client.get("/healthz")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "service": "operations-bff",
        "status": "ok",
        "capabilities": {
            "session": "ready",
            "login": "disabled",
            "overview": "enabled",
        },
    }
    assert rig.core.queries == [] and rig.twin.queries == []
    assert rig.client.post("/healthz").status_code == 405


def test_health_reports_disabled_capabilities_truthfully() -> None:
    assert health_body(login=True, overview=False)["capabilities"] == {
        "session": "ready",
        "login": "enabled",
        "overview": "disabled",
    }
    bare = Rig(overview=False).client.get("/healthz").json()
    assert bare["capabilities"]["overview"] == "disabled"


def test_health_is_not_a_browser_contract_operation() -> None:
    paths = {path for path, _, _ in operations().values()}
    assert "/healthz" not in paths


def test_outcome_classification() -> None:
    assert [outcome_of(s) for s in (200, 204, 302, 400, 401, 404, 500, 503)] == [
        "success",
        "success",
        "success",
        "client_error",
        "client_error",
        "client_error",
        "server_error",
        "server_error",
    ]
    record = access_record(
        method="GET",
        route="/x",
        operation_id=None,
        status=204,
        duration_ms=1.23456,
        correlation_id="c",
    )
    assert record["duration_ms"] == 1.235


def test_access_log_configuration_is_idempotent() -> None:
    logger = logging.getLogger(ACCESS_LOGGER)
    logger.handlers[:] = []
    configure_access_log()
    configure_access_log()
    assert len(logger.handlers) == 1
    assert logger.propagate is False
