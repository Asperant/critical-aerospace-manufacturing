"""Telemetry field standard: schemas plus the rules a schema cannot express.

The JSON Schemas in ``schemas/`` are the contract (``cap.resource/v1`` and
``cap.log/v1``). This module adds what structure alone cannot check
(01 Item 47 §34–§36): secret-bearing keys, secret-looking values and the size
bound that keeps logs from becoming a payload store.

Validation needs the ``validate`` extra (jsonschema); emitting telemetry never
does, so services do not pay for it at runtime.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator, Mapping
from functools import cache
from importlib import resources
from typing import Any, cast

LOG_SCHEMA = "log-record.schema.json"
RESOURCE_SCHEMA = "resource.schema.json"
MAX_RECORD_BYTES = 8192  # §34: logs are not a payload store

ENVIRONMENT_CLASSES = ("LOCAL", "INTEGRATION", "EVALUATION", "DEMO", "CI_EPHEMERAL")
SEVERITIES = ("DEBUG", "INFO", "WARN", "ERROR", "FATAL")

# §36: these never appear in logs or traces, under any spelling.
SECRET_KEY = re.compile(
    r"pass(word|wd)?|secret|token|api[_.-]?key|authorization|credential"
    r"|connection[_.-]?string|private[_.-]?key|cookie|session[_.-]?id",
    re.IGNORECASE,
)
SECRET_VALUE = (
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("GitHub token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer credential", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    ("URL credentials", re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@")),
    (
        "credential assignment",
        re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[=:]\s*\S+"),
    ),
)


class ValidationUnavailable(RuntimeError):
    """The ``validate`` extra (jsonschema) is not installed."""


@cache
def load_schema(name: str) -> dict[str, Any]:
    text = (
        resources.files("cap_observability")
        .joinpath("schemas", name)
        .read_text(encoding="utf-8")
    )
    return cast(dict[str, Any], json.loads(text))


def _schema_errors(name: str, instance: object) -> list[str]:
    try:
        from jsonschema import validators
    except ImportError as exc:  # pragma: no cover - exercised only without extra
        raise ValidationUnavailable(
            "install cap-observability[validate] to validate telemetry"
        ) from exc
    schema = load_schema(name)
    # jsonschema's public API is only partially typed; keep the boundary explicit.
    validator: Any = cast(Any, validators).validator_for(schema)(schema)
    errors: list[str] = []
    for error in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        where = ".".join(str(part) for part in error.path) or "<record>"
        errors.append(f"{where}: {error.message}")
    return errors


def _strings(value: object, path: str) -> Iterator[tuple[str, str]]:
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, Mapping):
        for key, item in cast(Mapping[object, object], value).items():
            yield from _strings(item, f"{path}.{key}" if path else str(key))
    elif isinstance(value, list):
        for index, item in enumerate(cast(list[object], value)):
            yield from _strings(item, f"{path}[{index}]")


def _secret_findings(record: Mapping[str, object]) -> list[str]:
    findings: list[str] = []
    attributes = record.get("attributes")
    if isinstance(attributes, Mapping):
        for key in cast(Mapping[object, object], attributes):
            if SECRET_KEY.search(str(key)):
                findings.append(
                    f"attributes.{key}: secret-bearing key is never logged (Item 47 §36)"
                )
    for path, text in _strings(record, ""):
        for label, pattern in SECRET_VALUE:
            if pattern.search(text):
                findings.append(f"{path}: looks like a {label}; never logged (§36)")
                break
    return findings


def check_log_record(record: object) -> list[str]:
    """All violations of ``cap.log/v1`` for one record; empty when it conforms."""
    errors = _schema_errors(LOG_SCHEMA, record)
    if isinstance(record, Mapping):
        errors += _secret_findings(cast(Mapping[str, object], record))
        size = len(json.dumps(record, ensure_ascii=False).encode("utf-8"))
        if size > MAX_RECORD_BYTES:
            errors.append(
                f"<record>: {size} bytes exceeds {MAX_RECORD_BYTES}; log a reference, "
                "not the payload (§34-§35)"
            )
    return errors


def check_resource(attributes: object) -> list[str]:
    """All violations of ``cap.resource/v1``; empty when the resource conforms."""
    return _schema_errors(RESOURCE_SCHEMA, attributes)


def check_log_lines(lines: Iterator[str] | list[str]) -> list[str]:
    """Check a JSON Lines stream; each finding names its 1-based line."""
    findings: list[str] = []
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            findings.append(f"line {number}: not JSON ({exc.msg})")
            continue
        findings += [f"line {number}: {error}" for error in check_log_record(record)]
    return findings
