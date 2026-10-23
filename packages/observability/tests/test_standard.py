from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from cap_observability import (
    MAX_RECORD_BYTES,
    check_log_lines,
    check_log_record,
    check_resource,
    load_schema,
)
from cap_observability.__main__ import main

PACKAGE = Path(__file__).resolve().parents[1]
SCHEMAS = PACKAGE / "src" / "cap_observability" / "schemas"


def example(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def minimal() -> dict[str, Any]:
    return {
        "timestamp": "2026-10-23T15:04:05Z",
        "severity": "INFO",
        "service": "manufacturing-core",
        "environment": "local-yavuz",
        "event_name": "core.health_checked",
        "message": "health probe finished",
    }


def test_published_examples_conform() -> None:
    assert check_log_record(example("log-record.json")) == []
    assert check_resource(example("resource.json")) == []
    assert check_log_record(minimal()) == []


@pytest.mark.parametrize(
    "field",
    ["timestamp", "severity", "service", "environment", "event_name", "message"],
)
def test_required_log_fields(field: str) -> None:
    record = minimal()
    del record[field]
    assert any(field in error for error in check_log_record(record))


LOG_BREAKAGES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("unknown field", lambda r: r.update(user="alice"), "Additional properties"),
    (
        "local time",
        lambda r: r.update(timestamp="2026-10-23T18:04:05+03:00"),
        "timestamp",
    ),
    ("lower severity", lambda r: r.update(severity="info"), "severity"),
    ("free event name", lambda r: r.update(event_name="Health checked"), "event_name"),
    ("one-part event", lambda r: r.update(event_name="health"), "event_name"),
    (
        "upper trace",
        lambda r: r.update(trace_id="4BF92F3577B34DA6A3CE929D0E0E4736"),
        "trace_id",
    ),
    ("zero trace", lambda r: r.update(trace_id="0" * 32), "trace_id"),
    ("span alone", lambda r: r.update(span_id="00f067aa0ba902b7"), "trace_id"),
    ("error no code", lambda r: r.update(severity="ERROR"), "error_code"),
    ("bad code", lambda r: r.update(error_code="timeout"), "error_code"),
    ("newline id", lambda r: r.update(correlation_id="a\nb"), "correlation_id"),
    ("long message", lambda r: r.update(message="x" * 2049), "message"),
    ("bad environment", lambda r: r.update(environment="Local Yavuz"), "environment"),
    ("bad class", lambda r: r.update(environment_class="PROD"), "environment_class"),
    (
        "too many refs",
        lambda r: r.update(
            entity_refs=[{"type": "Lot", "id": str(i)} for i in range(11)]
        ),
        "entity_refs",
    ),
    (
        "ref without id",
        lambda r: r.update(entity_refs=[{"type": "Lot"}]),
        "entity_refs",
    ),
    (
        "nested attribute",
        lambda r: r.update(attributes={"row": {"a": 1}}),
        "attributes",
    ),
    (
        "long attribute",
        lambda r: r.update(attributes={"note": "x" * 257}),
        "attributes",
    ),
    (
        "too many attributes",
        lambda r: r.update(attributes={f"k{i}": i for i in range(17)}),
        "attributes",
    ),
    ("attribute name", lambda r: r.update(attributes={"Bad Key": 1}), "attributes"),
]


@pytest.mark.parametrize(
    ("label", "mutate", "where"), LOG_BREAKAGES, ids=[b[0] for b in LOG_BREAKAGES]
)
def test_log_contract_violations(
    label: str, mutate: Callable[[dict[str, Any]], None], where: str
) -> None:
    record = minimal()
    mutate(record)
    errors = check_log_record(record)
    assert errors, label
    assert any(where in error for error in errors), errors


def test_error_with_code_conforms() -> None:
    record = minimal() | {"severity": "ERROR", "error_code": "DB_UNAVAILABLE"}
    assert check_log_record(record) == []


SECRETS: list[tuple[str, dict[str, Any]]] = [
    ("password key", {"attributes": {"db_password": "x"}}),
    ("token key", {"attributes": {"auth.token": "x"}}),
    ("api key", {"attributes": {"api_key": "x"}}),
    ("github token", {"message": "push with ghp_" + "a" * 36}),
    ("fine-grained pat", {"attributes": {"note": "github_pat_" + "A" * 30}}),
    ("aws key", {"message": "key AKIAABCDEFGHIJKLMNOP leaked"}),
    ("private key", {"message": "-----BEGIN OPENSSH PRIVATE KEY----- abc"}),
    ("bearer", {"attributes": {"header": "Bearer abcdefghijklmnop1234"}}),
    ("url credentials", {"message": "dsn postgresql://ci:s3cret@db:5432/core"}),
    ("assignment", {"message": "retry with password=hunter2"}),
]


@pytest.mark.parametrize(("label", "extra"), SECRETS, ids=[s[0] for s in SECRETS])
def test_secrets_are_violations(label: str, extra: dict[str, Any]) -> None:
    record = minimal()
    record.update(extra)
    errors = check_log_record(record)
    assert any("§36" in error for error in errors), (label, errors)


def test_ordinary_text_is_not_mistaken_for_a_secret() -> None:
    record = minimal() | {
        "message": "token bucket refilled for scheduler queue",
        "attributes": {"bucket_size": 10, "url": "http://otel-collector:4318/v1/logs"},
    }
    assert check_log_record(record) == []


def test_payload_size_bound() -> None:
    # Field limits count characters; the byte bound also covers multi-byte text.
    record = minimal() | {"attributes": {f"k{i}": "ş" * 256 for i in range(16)}}
    record["message"] = "ğ" * 2048
    size = len(json.dumps(record, ensure_ascii=False).encode())
    assert size > MAX_RECORD_BYTES
    assert any("§34" in error for error in check_log_record(record))


RESOURCE_BREAKAGES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("no class", lambda r: r.pop("cap.environment.class"), "cap.environment.class"),
    ("no environment", lambda r: r.pop("deployment.environment.name"), "deployment"),
    ("bad name", lambda r: r.update({"service.name": "Core_Service"}), "service.name"),
    (
        "profile as class",
        lambda r: r.update({"cap.environment.class": "core"}),
        "class",
    ),
    ("unknown profile", lambda r: r.update({"cap.runtime.profile": "gpu"}), "profile"),
    ("unknown key", lambda r: r.update({"host.ip": "10.0.0.1"}), "Additional"),
    (
        "evaluation without release",
        lambda r: r.update({"cap.environment.class": "EVALUATION"}),
        "cap.release.id",
    ),
    (
        "demo without release",
        lambda r: r.update({"cap.environment.class": "DEMO"}),
        "cap.release.id",
    ),
]


@pytest.mark.parametrize(
    ("label", "mutate", "where"),
    RESOURCE_BREAKAGES,
    ids=[b[0] for b in RESOURCE_BREAKAGES],
)
def test_resource_contract_violations(
    label: str, mutate: Callable[[dict[str, Any]], None], where: str
) -> None:
    resource = copy.deepcopy(example("resource.json"))
    mutate(resource)
    errors = check_resource(resource)
    assert any(where in error for error in errors), (label, errors)


def test_evaluation_with_release_conforms() -> None:
    resource = example("resource.json") | {
        "cap.environment.class": "EVALUATION",
        "deployment.environment.name": "eval-rc090-001",
        "cap.release.id": "rc-0.9.0",
    }
    assert check_resource(resource) == []


def test_log_and_resource_share_identity_rules() -> None:
    log = load_schema("log-record.schema.json")["properties"]
    resource = load_schema("resource.schema.json")["properties"]
    pairs = [
        ("service", "service.name"),
        ("environment", "deployment.environment.name"),
        ("environment_class", "cap.environment.class"),
        ("release", "cap.release.id"),
    ]
    for log_field, attribute in pairs:
        assert {k: v for k, v in log[log_field].items() if k != "description"} == {
            k: v for k, v in resource[attribute].items() if k != "description"
        }, log_field


def documented(section: str) -> set[str]:
    text = (PACKAGE / "README.md").read_text(encoding="utf-8")
    body = text.split(section, 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([^`]+)` \|", body, flags=re.MULTILINE))


def test_readme_documents_exactly_the_contract() -> None:
    assert documented("## Log record") == set(
        load_schema("log-record.schema.json")["properties"]
    )
    assert documented("## Resource attributes") == set(
        load_schema("resource.schema.json")["properties"]
    )


def test_log_lines_report_line_numbers() -> None:
    good = json.dumps(minimal())
    bad = json.dumps(minimal() | {"severity": "LOUD"})
    findings = check_log_lines([good, "", bad, "{not json"])
    assert findings[0].startswith("line 3: severity")
    assert findings[-1].startswith("line 4: not JSON")


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    good = tmp_path / "good.jsonl"
    good.write_text(json.dumps(minimal()) + "\n", encoding="utf-8")
    bad = tmp_path / "bad.jsonl"
    bad.write_text(json.dumps(minimal() | {"service": "X"}) + "\n", encoding="utf-8")
    assert main(["check-logs", str(good)]) == 0
    assert "1 records conform" in capsys.readouterr().out
    assert main(["check-logs", str(good), str(bad)]) == 1
    assert "line 1: service" in capsys.readouterr().out
    assert main(["check-logs", str(tmp_path / "missing.jsonl")]) == 2
    assert main(["lint"]) == 2
