"""Map the field standard onto OTLP/JSON (OpenTelemetry Protocol, JSON encoding).

A ``cap.log/v1`` record becomes one OTLP log record: ``timestamp`` → time,
``severity`` → severity text and number, ``message`` → body, ``trace_id`` and
``span_id`` → the record's trace context, and every other context field → an
attribute with the same name. ``service`` and ``environment`` travel as resource
attributes (``cap.resource/v1``), so they are dropped from the record itself.

Standard library only: services can emit without installing jsonschema.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

SEVERITY_NUMBER = {"DEBUG": 5, "INFO": 9, "WARN": 13, "ERROR": 17, "FATAL": 21}
_RECORD_TOP_LEVEL = {"timestamp", "severity", "message", "trace_id", "span_id"}
_FROM_RESOURCE = {
    "service",
    "environment",
    "service_version",
    "environment_class",
    "release",
}


def any_value(value: object) -> dict[str, Any]:
    """One OTLP ``AnyValue``; nested structures are not part of the standard."""
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if value is None:
        return {}
    return {"stringValue": str(value)}


def key_values(attributes: Mapping[str, object]) -> list[dict[str, Any]]:
    return [
        {"key": key, "value": any_value(value)} for key, value in attributes.items()
    ]


def unix_nanos(timestamp: str) -> str:
    """RFC 3339 ``...Z`` → integer nanoseconds as a string (OTLP/JSON rule)."""
    whole, _, fraction = timestamp.removesuffix("Z").partition(".")
    seconds = int(datetime.fromisoformat(whole + "+00:00").timestamp())
    nanos = int((fraction or "0").ljust(9, "0")[:9])
    return str(seconds * 1_000_000_000 + nanos)


def log_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """OTLP ``LogRecord`` for one conforming ``cap.log/v1`` record."""
    attributes: dict[str, object] = {}
    for key, value in record.items():
        if key in _RECORD_TOP_LEVEL or key in _FROM_RESOURCE:
            continue
        if key == "entity_refs":
            for index, ref in enumerate(value):
                attributes[f"entity_ref.{index}"] = f"{ref['type']}:{ref['id']}"
        elif key == "attributes":
            attributes.update(value)
        else:
            attributes[key] = value
    otlp: dict[str, Any] = {
        "timeUnixNano": unix_nanos(record["timestamp"]),
        "severityText": record["severity"],
        "severityNumber": SEVERITY_NUMBER[record["severity"]],
        "body": {"stringValue": record["message"]},
        "attributes": key_values(attributes),
    }
    if "trace_id" in record:
        otlp["traceId"] = record["trace_id"]
    if "span_id" in record:
        otlp["spanId"] = record["span_id"]
    return otlp


def logs_request(
    resource: Mapping[str, object], records: list[Mapping[str, Any]], scope: str
) -> dict[str, Any]:
    """OTLP ``ExportLogsServiceRequest`` (POST /v1/logs, application/json)."""
    return {
        "resourceLogs": [
            {
                "resource": {"attributes": key_values(resource)},
                "scopeLogs": [
                    {
                        "scope": {"name": scope},
                        "logRecords": [log_record(r) for r in records],
                    }
                ],
            }
        ]
    }
