"""Telemetry pipeline smoke against a REAL Collector and OpenObserve (WP-OBS-001).

Boundary mode REAL (03: TEST-OBS-TELEMETRY, AV-SCEN-01): one conforming log
record, one span and one counter are sent as OTLP/HTTP to the Collector and must
become queryable in OpenObserve. Missing services FAIL, never skip.

Run after ``infra/observability/stack.sh up`` with its ``env`` output exported:

    eval "$(infra/observability/stack.sh env | sed 's/^/export /')"
    uv run --project ci --locked python -m pytest infra/observability/tests -m integration
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

import pytest
from cap_observability import check_log_record, check_resource
from cap_observability.otlp import key_values, logs_request, unix_nanos

pytestmark = pytest.mark.integration
DEADLINE_S = 90


def required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.fail(
            f"{name} is not set: run infra/observability/stack.sh up and export its env"
        )
    return value


def request(url: str, payload: object, headers: dict[str, str]) -> tuple[int, Any]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", **headers}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            body = response.read()
            return response.status, json.loads(body) if body.strip() else None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")[:500]


class OpenObserve:
    def __init__(self) -> None:
        self.url = required("O2_URL")
        token = f"{required('O2_ROOT_EMAIL')}:{required('O2_ROOT_PASSWORD')}"
        self.auth = {
            "Authorization": "Basic " + base64.b64encode(token.encode()).decode()
        }

    def search(self, stream_type: str, sql: str) -> list[dict[str, Any]]:
        now = int(time.time() * 1_000_000)
        payload = {
            "query": {
                "sql": sql,
                "start_time": now - 15 * 60 * 1_000_000,
                "end_time": now + 5 * 60 * 1_000_000,
                "from": 0,
                "size": 10,
            }
        }
        status, body = request(
            f"{self.url}/api/default/_search?type={stream_type}", payload, self.auth
        )
        if status != 200 or not isinstance(body, dict):
            return []  # stream not created yet, or not searchable yet
        return list(body.get("hits", []))

    def wait_for(self, stream_type: str, sql: str) -> dict[str, Any]:
        deadline = time.monotonic() + DEADLINE_S
        while time.monotonic() < deadline:
            hits = self.search(stream_type, sql)
            if hits:
                return hits[0]
            time.sleep(2)
        streams = self.streams(stream_type)
        pytest.fail(
            f"no {stream_type} hit within {DEADLINE_S}s for: {sql}\nstreams: {streams}"
        )

    def streams(self, stream_type: str) -> object:
        req = urllib.request.Request(
            f"{self.url}/api/default/streams?type={stream_type}", headers=self.auth
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                data = json.loads(response.read())
            return [s.get("name") for s in data.get("list", [])]
        except (urllib.error.URLError, ValueError) as exc:
            return f"unavailable: {exc}"


@pytest.fixture(scope="module")
def run() -> dict[str, Any]:
    """Send one log, one span and one counter with shared identities."""
    collector = required("OTLP_HTTP_URL")
    in_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    run_id = "obs-smoke-" + secrets.token_hex(6)
    trace_id, span_id = secrets.token_hex(16), secrets.token_hex(8)
    resource = {
        "service.name": "obs-smoke",
        "service.version": "0.1.0",
        "deployment.environment.name": "ci-obs-smoke" if in_ci else "local-obs-smoke",
        "cap.environment.class": "CI_EPHEMERAL" if in_ci else "LOCAL",
    }
    now = datetime.now(UTC)
    record = {
        "timestamp": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "severity": "INFO",
        "service": resource["service.name"],
        "environment": resource["deployment.environment.name"],
        "event_name": "observability.smoke_emitted",
        "message": "telemetry pipeline smoke record",
        "trace_id": trace_id,
        "span_id": span_id,
        "correlation_id": run_id,
        "attributes": {"smoke_run": run_id},
    }
    assert check_resource(resource) == []
    assert check_log_record(record) == []
    start = unix_nanos(record["timestamp"])
    end = str(int(start) + 5_000_000)
    span = {
        "resourceSpans": [
            {
                "resource": {"attributes": key_values(resource)},
                "scopeSpans": [
                    {
                        "scope": {"name": "obs-smoke"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": "observability.smoke",
                                "kind": 1,
                                "startTimeUnixNano": start,
                                "endTimeUnixNano": end,
                                "attributes": key_values({"smoke_run": run_id}),
                            }
                        ],
                    }
                ],
            }
        ]
    }
    counter = {
        "resourceMetrics": [
            {
                "resource": {"attributes": key_values(resource)},
                "scopeMetrics": [
                    {
                        "scope": {"name": "obs-smoke"},
                        "metrics": [
                            {
                                "name": "cap.obs.smoke_events",
                                "unit": "1",
                                "sum": {
                                    "aggregationTemporality": 2,
                                    "isMonotonic": True,
                                    "dataPoints": [
                                        {
                                            "asInt": "1",
                                            "startTimeUnixNano": start,
                                            "timeUnixNano": end,
                                            "attributes": key_values(
                                                {"smoke_run": run_id}
                                            ),
                                        }
                                    ],
                                },
                            }
                        ],
                    }
                ],
            }
        ]
    }
    sent = {
        "logs": request(
            f"{collector}/v1/logs", logs_request(resource, [record], "obs-smoke"), {}
        ),
        "traces": request(f"{collector}/v1/traces", span, {}),
        "metrics": request(f"{collector}/v1/metrics", counter, {}),
    }
    return {"run_id": run_id, "trace_id": trace_id, "resource": resource, "sent": sent}


def test_collector_accepts_all_three_signals(run: dict[str, Any]) -> None:
    for signal, (status, body) in run["sent"].items():
        assert status == 200, f"{signal}: HTTP {status} {body}"


def test_log_record_is_queryable_with_its_context(run: dict[str, Any]) -> None:
    hit = OpenObserve().wait_for(
        "logs", f"SELECT * FROM \"default\" WHERE correlation_id = '{run['run_id']}'"
    )
    assert hit.get("service_name") == "obs-smoke"
    assert (
        hit.get("deployment_environment_name")
        == run["resource"]["deployment.environment.name"]
    )
    assert hit.get("event_name") == "observability.smoke_emitted"
    assert hit.get("trace_id") == run["trace_id"]


def test_span_is_queryable_by_trace_id(run: dict[str, Any]) -> None:
    hit = OpenObserve().wait_for(
        "traces", f"SELECT * FROM \"default\" WHERE trace_id = '{run['trace_id']}'"
    )
    assert hit.get("service_name") == "obs-smoke"


def test_counter_is_queryable(run: dict[str, Any]) -> None:
    hit = OpenObserve().wait_for(
        "metrics",
        f"SELECT * FROM \"cap_obs_smoke_events\" WHERE smoke_run = '{run['run_id']}'",
    )
    assert hit.get("service_name") == "obs-smoke"
