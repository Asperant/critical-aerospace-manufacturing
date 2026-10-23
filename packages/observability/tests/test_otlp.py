from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cap_observability.otlp import any_value, log_record, logs_request, unix_nanos

EXAMPLE = Path(__file__).resolve().parents[1] / "src/cap_observability/schemas"


def example() -> dict[str, Any]:
    return json.loads((EXAMPLE / "log-record.json").read_text("utf-8"))


def attributes(otlp: dict[str, Any]) -> dict[str, Any]:
    return {kv["key"]: kv["value"] for kv in otlp["attributes"]}


def test_timestamp_becomes_unix_nanoseconds() -> None:
    assert unix_nanos("1970-01-01T00:00:01Z") == "1000000000"
    assert unix_nanos("2026-10-23T15:04:05.123Z") == "1792767845123000000"
    assert unix_nanos("2026-10-23T15:04:05.123456789Z").endswith("123456789")


def test_any_value_types() -> None:
    assert any_value(True) == {"boolValue": True}
    assert any_value(3) == {"intValue": "3"}
    assert any_value(1.5) == {"doubleValue": 1.5}
    assert any_value("x") == {"stringValue": "x"}
    assert any_value(None) == {}


def test_record_maps_to_otlp_fields_and_attributes() -> None:
    record = example()
    otlp = log_record(record)
    assert otlp["severityText"] == "ERROR" and otlp["severityNumber"] == 17
    assert otlp["body"] == {"stringValue": record["message"]}
    assert otlp["traceId"] == record["trace_id"]
    assert otlp["spanId"] == record["span_id"]
    attrs = attributes(otlp)
    assert attrs["event_name"] == {"stringValue": "scheduler.validation_failed"}
    assert attrs["correlation_id"] == {"stringValue": record["correlation_id"]}
    assert attrs["error_code"] == {"stringValue": "SCHEDULE_INFEASIBLE"}
    assert attrs["entity_ref.0"] == {"stringValue": "Equipment:CNC-5AX-07"}
    assert attrs["candidate_count"] == {"intValue": "3"}
    # identity travels in the resource, never duplicated per record
    for moved in ("service", "environment", "service_version", "environment_class"):
        assert moved not in attrs
    for top in ("timestamp", "severity", "message", "trace_id", "span_id"):
        assert top not in attrs


def test_record_without_trace_context() -> None:
    record = example()
    del record["trace_id"], record["span_id"]
    otlp = log_record(record)
    assert "traceId" not in otlp and "spanId" not in otlp


def test_logs_request_carries_resource_once() -> None:
    resource = {"service.name": "scheduler-service", "cap.environment.class": "LOCAL"}
    body = logs_request(resource, [example(), example()], "unit")
    (resource_logs,) = body["resourceLogs"]
    keys = [kv["key"] for kv in resource_logs["resource"]["attributes"]]
    assert keys == ["service.name", "cap.environment.class"]
    (scope,) = resource_logs["scopeLogs"]
    assert scope["scope"] == {"name": "unit"}
    assert len(scope["logRecords"]) == 2
