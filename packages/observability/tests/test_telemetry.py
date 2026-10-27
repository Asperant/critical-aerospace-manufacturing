from __future__ import annotations

import io
import json
import logging
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import cap_observability.telemetry as telemetry_module
import pytest
from cap_observability import check_log_lines, check_log_record, check_resource
from cap_observability.telemetry import (
    UNCLASSIFIED_ERROR,
    JsonFormatter,
    OtlpLogHandler,
    build_record,
    configure,
    resource_from_env,
)
from opentelemetry.sdk.trace import TracerProvider

LOCAL = {"USER": "yavuz"}


def resource() -> dict[str, str]:
    return resource_from_env("manufacturing-core", "0.1.0", LOCAL)


def make(
    message: str = "query finished",
    level: int = logging.INFO,
    name: str = "manufacturing_core",
    exc_info: Any = None,
    **extra: Any,
) -> logging.LogRecord:
    record = logging.LogRecord(name, level, __file__, 1, message, None, exc_info)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


# ---------------------------------------------------------------- resource ---


def test_local_default_environment_conforms() -> None:
    res = resource()
    assert res["deployment.environment.name"] == "local-yavuz"
    assert res["cap.environment.class"] == "LOCAL"
    assert check_resource(res) == []


def test_explicit_environment_and_optional_identities() -> None:
    res = resource_from_env(
        "scheduler-service",
        "0.2.0",
        {
            "CAP_ENVIRONMENT": "eval-rc090-001",
            "CAP_ENVIRONMENT_CLASS": "EVALUATION",
            "CAP_RELEASE_ID": "rc-0.9.0",
            "CAP_RUNTIME_PROFILE": "planning",
        },
    )
    assert check_resource(res) == []
    assert res["cap.release.id"] == "rc-0.9.0"


@pytest.mark.parametrize(
    ("environ", "problem"),
    [
        ({"CAP_ENVIRONMENT_CLASS": "INTEGRATION"}, "CAP_ENVIRONMENT is required"),
        (
            {"CAP_ENVIRONMENT": "eval-1", "CAP_ENVIRONMENT_CLASS": "EVALUATION"},
            "require CAP_RELEASE_ID",
        ),
        ({"CAP_ENVIRONMENT_CLASS": "PROD"}, "is not one of"),
        ({"CAP_ENVIRONMENT": "Integration Main"}, "does not match"),
        ({"CAP_RUNTIME_PROFILE": "gpu"}, "cap.runtime.profile"),
    ],
)
def test_invalid_environment_is_refused(environ: dict[str, str], problem: str) -> None:
    with pytest.raises(ValueError, match=problem):
        resource_from_env("manufacturing-core", "0.1.0", LOCAL | environ)


def test_unusual_user_name_still_gives_a_valid_local_id() -> None:
    res = resource_from_env("manufacturing-core", "0.1.0", {"USER": "Yavuz Gümüş!"})
    assert check_resource(res) == []


# ------------------------------------------------------------------ record ---


def test_plain_record_conforms_with_default_event_name() -> None:
    out = build_record(make(), resource())
    assert check_log_record(out) == []
    assert out["event_name"] == "manufacturing_core.log"
    assert out["service"] == "manufacturing-core"
    assert out["environment"] == "local-yavuz"
    assert out["environment_class"] == "LOCAL"
    assert "trace_id" not in out


def test_context_fields_are_carried() -> None:
    out = build_record(
        make(
            event_name="core.query_completed",
            correlation_id="incident-7",
            world_id="PRIMARY",
            entity_refs=[{"type": "Lot", "id": "LOT-1"}],
            attributes={"duration_ms": 12.5, "outcome": "READY"},
        ),
        resource(),
    )
    assert check_log_record(out) == []
    assert out["event_name"] == "core.query_completed"
    assert out["correlation_id"] == "incident-7"
    assert out["entity_refs"] == [{"type": "Lot", "id": "LOT-1"}]
    assert out["attributes"] == {"duration_ms": 12.5, "outcome": "READY"}


def test_invalid_context_is_dropped_not_fatal() -> None:
    out = build_record(
        make(
            event_name="Not An Event",
            correlation_id="bad\nid",
            entity_refs=[{"type": "lot", "id": "x"}, "junk"],
            attributes={"Bad Key": 1, "nested": {"a": 1}},
        ),
        resource(),
    )
    assert check_log_record(out) == []
    assert "correlation_id" not in out and "entity_refs" not in out
    assert "attributes" not in out
    assert out["event_name"] == "manufacturing_core.log"


def test_exception_gets_type_and_stable_code() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        out = build_record(
            make("lookup failed", logging.ERROR, exc_info=sys.exc_info()), resource()
        )
    assert check_log_record(out) == []
    assert out["error_type"] == "ValueError"
    assert out["error_code"] == UNCLASSIFIED_ERROR


def test_given_error_code_is_kept() -> None:
    out = build_record(
        make("db down", logging.CRITICAL, error_code="DB_UNAVAILABLE"), resource()
    )
    assert out["severity"] == "FATAL"
    assert out["error_code"] == "DB_UNAVAILABLE"


def test_secrets_never_leave_the_process() -> None:
    out = build_record(
        make(
            "connect postgresql://core:s3cret@db/core with password=hunter2",
            attributes={"api_token": "abc", "note": "ghp_" + "a" * 36},
        ),
        resource(),
    )
    assert check_log_record(out) == []
    text = json.dumps(out)
    for secret in ("s3cret", "hunter2", "api_token", "ghp_"):
        assert secret not in text
    assert "[REDACTED]" in text


def test_oversized_record_is_bounded() -> None:
    out = build_record(
        make("ğ" * 4000, attributes={f"k{i}": "ş" * 256 for i in range(16)}),
        resource(),
    )
    assert check_log_record(out) == []


def test_trace_context_from_the_current_span() -> None:
    tracer = TracerProvider().get_tracer("unit")
    with tracer.start_as_current_span("work") as span:
        out = build_record(make(), resource())
    context = span.get_span_context()
    assert out["trace_id"] == format(context.trace_id, "032x")
    assert out["span_id"] == format(context.span_id, "016x")
    assert check_log_record(out) == []


# --------------------------------------------------------------- configure ---


@pytest.fixture
def clean_root() -> Iterator[None]:
    root = logging.getLogger()
    before, level = list(root.handlers), root.level
    yield
    for handler in list(root.handlers):
        if handler not in before:
            root.removeHandler(handler)
    root.setLevel(level)


@pytest.mark.usefixtures("clean_root")
def test_configure_writes_standard_lines_to_stdout() -> None:
    stream = io.StringIO()
    telemetry = configure("manufacturing-core", "0.1.0", environ=LOCAL, stream=stream)
    log = logging.getLogger("manufacturing_core.health")
    log.info(
        "probe", extra={"event_name": "core.health_checked", "correlation_id": "h-1"}
    )
    log.warning("slow")
    telemetry.shutdown()
    lines = stream.getvalue().splitlines()
    assert len(lines) == 2
    assert check_log_lines(lines) == []
    first = json.loads(lines[0])
    assert first["event_name"] == "core.health_checked"
    assert json.loads(lines[1])["severity"] == "WARN"
    assert telemetry.endpoint is None and telemetry.providers == []


@pytest.mark.usefixtures("clean_root")
def test_configure_twice_replaces_only_its_own_handlers() -> None:
    root = logging.getLogger()
    foreign = logging.NullHandler()
    root.addHandler(foreign)
    configure("manufacturing-core", "0.1.0", environ=LOCAL, stream=io.StringIO())
    telemetry = configure(
        "manufacturing-core", "0.1.0", environ=LOCAL, stream=io.StringIO()
    )
    ours = [h for h in root.handlers if getattr(h, "_cap_observability", False)]
    assert len(ours) == 1 and foreign in root.handlers
    telemetry.shutdown()
    assert not [h for h in root.handlers if getattr(h, "_cap_observability", False)]


def test_formatter_never_produces_a_nonconforming_line() -> None:
    formatter = JsonFormatter(resource())
    line = formatter.format(make("", logging.DEBUG, name="9weird-name"))
    record = json.loads(line)
    assert check_log_record(record) == []
    assert record["event_name"] == "app_9weird_name.log"


# ------------------------------------------------------------- OTLP shipping ---


class FakePost:
    def __init__(self, status: int = 200, error: Exception | None = None) -> None:
        self.status, self.error = status, error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __call__(self, url: str, body: bytes, timeout: float) -> int:
        self.calls.append((url, json.loads(body)))
        if self.error:
            raise self.error
        return self.status


def handler_with(post: FakePost, **kwargs: Any) -> OtlpLogHandler:
    return OtlpLogHandler(
        "http://collector:4318/", resource(), interval_s=3600, post=post, **kwargs
    )


def test_batches_are_otlp_with_resource_once() -> None:
    post = FakePost()
    handler = handler_with(post)
    for i in range(3):
        handler.emit(make(f"m{i}", correlation_id=f"c-{i}"))
    handler.flush()
    handler.close()
    ((url, payload),) = post.calls
    assert url == "http://collector:4318/v1/logs"
    (resource_logs,) = payload["resourceLogs"]
    keys = {kv["key"] for kv in resource_logs["resource"]["attributes"]}
    assert {"service.name", "deployment.environment.name"} <= keys
    assert len(resource_logs["scopeLogs"][0]["logRecords"]) == 3
    assert handler.sent == 3 and handler.dropped == 0


def test_unreachable_collector_drops_and_warns_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    post = FakePost(error=OSError("connection refused"))
    handler = handler_with(post, batch_size=1)
    handler.emit(make("a"))
    handler.emit(make("b"))
    handler.flush()  # must not raise into the application
    handler.close()
    assert handler.dropped == 2 and handler.sent == 0
    assert capsys.readouterr().err.count("cap_observability:") == 1


def test_first_warning_is_not_suppressed_on_a_fresh_monotonic_clock(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(telemetry_module.time, "monotonic", lambda: 1.0)
    post = FakePost(error=OSError("connection refused"))
    handler = handler_with(post, batch_size=1)
    handler.emit(make("a"))
    handler.flush()
    handler.close()
    assert capsys.readouterr().err.count("cap_observability:") == 1


def test_rejection_counts_as_dropped() -> None:
    post = FakePost(status=400)
    handler = handler_with(post)
    handler.emit(make("a"))
    handler.flush()
    handler.close()
    assert handler.dropped == 1


def test_full_queue_drops_instead_of_blocking() -> None:
    post = FakePost()
    handler = handler_with(post, queue_size=2)
    for _ in range(5):
        handler.emit(make("x"))
    assert handler.dropped == 3
    handler.close()
    assert handler.sent == 2


def test_real_http_post_reaches_a_listening_server() -> None:
    received: list[dict[str, Any]] = []

    class Sink(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802 - http.server API
            length = int(self.headers["Content-Length"])
            received.append(json.loads(self.rfile.read(length)))
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            pass

    server = HTTPServer(("127.0.0.1", 0), Sink)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        handler = OtlpLogHandler(
            f"http://127.0.0.1:{server.server_port}", resource(), interval_s=3600
        )
        handler.emit(make("over the wire"))
        handler.close()
    finally:
        server.shutdown()
    assert handler.sent == 1
    body = received[0]["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]["body"]
    assert body == {"stringValue": "over the wire"}


@pytest.mark.usefixtures("clean_root")
def test_endpoint_enables_otlp_logs_traces_and_metrics() -> None:
    import time

    telemetry = configure(
        "manufacturing-core",
        "0.1.0",
        environ=LOCAL | {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://127.0.0.1:9/"},
        stream=io.StringIO(),
    )
    assert telemetry.endpoint == "http://127.0.0.1:9"
    assert any(isinstance(h, OtlpLogHandler) for h in telemetry.handlers)
    assert [type(p).__name__ for p in telemetry.providers] == [
        "TracerProvider",
        "MeterProvider",
    ]
    started = time.monotonic()
    telemetry.shutdown()  # an unreachable Collector must not hang the service
    assert time.monotonic() - started < 15
