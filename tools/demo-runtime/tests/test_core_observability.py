from __future__ import annotations

import json
from typing import Literal, cast

import pytest
from cap_demo_runtime import core_api
from cap_observability.standard import check_health_report, check_log_lines
from fastapi.testclient import TestClient
from manufacturing_core.observability import CoreHealth


@pytest.mark.parametrize(
    ("database_status", "http_status"),
    [("READY", 200), ("UNAVAILABLE", 503)],
)
def test_core_health_endpoint_reports_database_readiness_and_standard_logs(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    database_status: str,
    http_status: int,
) -> None:
    monkeypatch.setenv("CAP_PG_DSN", "postgresql://core.invalid/cap")
    monkeypatch.setenv("CAP_ENVIRONMENT", "core-demo-test")
    monkeypatch.setenv("CAP_ENVIRONMENT_CLASS", "DEMO")
    monkeypatch.setenv("CAP_RELEASE_ID", "test-0.1.0")
    monkeypatch.setattr(
        core_api,
        "core_health",
        lambda _dsn, correlation_id: CoreHealth(
            cast(Literal["READY", "UNAVAILABLE"], database_status), correlation_id
        ),
    )

    with TestClient(core_api.create_app()) as client:
        response = client.get("/healthz")

    report = response.json()
    assert response.status_code == http_status
    assert check_health_report(report) == []
    assert report["schema"] == "cap.health/v1"
    assert report["service"] == "manufacturing-core"
    assert report["environment"] == "core-demo-test"
    assert report["status"] == database_status
    assert report["correlation_id"] == response.headers["X-Correlation-Id"]
    lines = capsys.readouterr().out.splitlines()
    assert check_log_lines(lines) == []
    access = next(
        record
        for record in map(json.loads, lines)
        if record["event_name"] == "http.request"
    )
    assert access["correlation_id"] == report["correlation_id"]
    assert access["attributes"]["route"] == "/healthz"
