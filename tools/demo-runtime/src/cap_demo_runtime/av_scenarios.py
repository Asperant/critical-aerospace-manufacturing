"""Focused, real-runtime AV-SCEN acceptance slices for WP-CORE-008.

The canonical AV-SCEN names cover the wider platform.  This module deliberately
reports only the Core/outbox/JetStream/Twin/BFF/UI slice that exists in the
merged demo runtime.  It never creates a mock broker/database/identity boundary
and it never treats a partial slice as the complete architecture scenario.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

import nats
import psycopg
from psycopg.rows import DictRow, dict_row

WORLD_ID = "DEMO-WORLD"
BRANCH_ID = "PRIMARY"
CONSUMER_SCOPE = "twin-primary"
MAIN_SHA = "ee060997b611fae16d6c4f13c0d85cebafaf17e7"
DEFAULT_BROWSER_EVIDENCE = "evidence/WP-CORE-008/RUNTIME-E2E-2026-10-29.md"
DEFAULT_DISPATCH_EVIDENCE = "evidence/WP-CORE-008/DEP-028-CURRENT-MAIN-2026-10-29.md"


class ScenarioFailure(RuntimeError):
    pass


def _connect(dsn: str) -> psycopg.Connection[DictRow]:
    return psycopg.Connection[DictRow].connect(
        dsn, row_factory=dict_row, connect_timeout=10
    )


def _env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ScenarioFailure(
            f"runtime credential file unreadable: {path}: {exc}"
        ) from exc
    for line in lines:
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _runtime_dsn(env_name: str, file_name: str, user: str) -> str:
    explicit = os.environ.get(env_name, "").strip()
    if explicit:
        return explicit
    state_dir = Path(
        os.environ.get("CAP_PLATFORM_STATE_DIR", "~/.local/state/cap-platform")
    ).expanduser()
    values = _env_file(state_dir / file_name)
    password = values.get(
        "CAP_PG_PASSWORD"
        if file_name in {"demo-core.env", "demo-twin.env"}
        else (
            "CAP_CORE_RUNTIME_PASSWORD"
            if user == "cap_core_runtime"
            else "CAP_TWIN_RUNTIME_PASSWORD"
        ),
        "",
    )
    if not password:
        raise ScenarioFailure(f"{user} runtime credential is absent from {file_name}")
    port = os.environ.get("CAP_PG_PORT", "25432")
    return f"postgresql://{quote(user)}:{quote(password)}@127.0.0.1:{port}/cap"


def _core_dsn() -> str:
    return _runtime_dsn("CAP_AV_CORE_DSN", "demo-core.env", "cap_core_runtime")


def _twin_dsn() -> str:
    return _runtime_dsn("CAP_AV_TWIN_DSN", "demo-twin.env", "cap_twin_runtime")


def _http(
    url: str, *, method: str = "GET", body: dict[str, Any] | None = None
) -> tuple[int, bytes]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise ScenarioFailure(f"runtime HTTP unavailable: {url}: {exc}") from exc


def _json_body(raw: bytes, context: str) -> dict[str, Any]:
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ScenarioFailure(f"{context} did not return JSON") from exc
    if not isinstance(body, dict):
        raise ScenarioFailure(f"{context} JSON response is not an object")
    return body


def _state(connection: psycopg.Connection[Any], lot_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        "SELECT l.id, l.revision, s.revision AS state_revision, "
        "s.lifecycle_state, s.execution_state, "
        "EXISTS (SELECT 1 FROM core.material_hold h "
        "WHERE h.lot_id=l.id AND h.status='ACTIVE') AS held "
        "FROM core.lot l JOIN core.lot_state s ON s.id=l.id WHERE l.id=%s",
        (lot_id,),
    ).fetchone()
    return None if row is None else dict(row)


def _seed_lot(lot_id: str, revision: str) -> None:
    with _connect(_core_dsn()) as connection:
        if _state(connection, lot_id) is not None:
            raise ScenarioFailure(f"deterministic lot already exists: {lot_id}")
        with connection.transaction():
            connection.execute(
                "INSERT INTO core.lot(id, revision, order_id) "
                "VALUES (%s, %s, 'DEMO-ORDER-001')",
                (lot_id, revision),
            )
            connection.execute(
                "INSERT INTO core.lot_state(id, revision) VALUES (%s, %s)",
                (lot_id, revision),
            )


def _wait_for_rows(lot_id: str, event_id: str, timeout: float = 20.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with _connect(_core_dsn()) as core:
            outbox = core.execute(
                "SELECT outbox_id, event_id, event_type, aggregate_id, "
                "aggregate_version, world_id, correlation_id, causation_id, "
                "publication_status, event FROM core.outbox WHERE event_id=%s",
                (event_id,),
            ).fetchone()
        with _connect(_twin_dsn()) as twin:
            applied = twin.execute(
                "SELECT consumer_scope, event_id, world_id, branch_id, "
                "aggregate_type, aggregate_id, aggregate_version "
                "FROM twin.applied_event WHERE event_id=%s AND consumer_scope=%s",
                (event_id, CONSUMER_SCOPE),
            ).fetchone()
            projection = twin.execute(
                "SELECT aggregate_id, world_id, branch_id, aggregate_version, "
                "state, source_event_id, source_revision "
                "FROM twin.projection_entity WHERE aggregate_id=%s "
                "AND world_id=%s AND branch_id=%s",
                (lot_id, WORLD_ID, BRANCH_ID),
            ).fetchone()
            revision = twin.execute(
                "SELECT source_event_id, status FROM twin.projection_revision "
                "WHERE world_id=%s AND branch_id=%s",
                (WORLD_ID, BRANCH_ID),
            ).fetchone()
        if (
            outbox is not None
            and outbox["publication_status"] == "PUBLISHED"
            and applied
            and projection
        ):
            return {
                "outbox": dict(outbox),
                "twin_applied_event": dict(applied),
                "twin_projection": dict(projection),
                "twin_revision": None if revision is None else dict(revision),
            }
        time.sleep(0.25)
    raise ScenarioFailure(f"event did not reach published Twin projection: {event_id}")


async def _nats_info() -> dict[str, Any]:
    url = os.environ.get("CAP_AV_NATS_URL", "nats://127.0.0.1:24222")
    nc = await nats.connect(url, connect_timeout=10)
    try:
        js = nc.jetstream()
        stream = await js.stream_info("CAP_EVENTS")
        consumer = await js.consumer_info("CAP_EVENTS", CONSUMER_SCOPE)
        return {
            "url": url.split("@")[-1],
            "stream": stream.config.name,
            "subjects": list(stream.config.subjects or []),
            "messages": stream.state.messages,
            "durable": consumer.name,
            "ack_policy": str(consumer.config.ack_policy),
            "deliver_policy": str(consumer.config.deliver_policy),
            "consumer_sequence": (
                consumer.delivered.consumer_seq if consumer.delivered else None
            ),
            "stream_sequence": (
                consumer.delivered.stream_seq if consumer.delivered else None
            ),
            "num_ack_pending": consumer.num_ack_pending,
            "num_redelivered": consumer.num_redelivered,
        }
    finally:
        await nc.drain()


def _surface_checks(browser_path: Path) -> dict[str, Any]:
    keycloak_port = os.environ.get("CAP_KEYCLOAK_PORT", "28080")
    ui_port = os.environ.get("CAP_UI_PORT", "29080")
    # The demo Keycloak image exposes the imported realm on the published port;
    # its management health endpoint is intentionally not published by Compose.
    keycloak_status, _ = _http(f"http://127.0.0.1:{keycloak_port}/realms/cap-platform")
    ui_status, _ = _http(f"http://127.0.0.1:{ui_port}/")
    try:
        browser_text = browser_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ScenarioFailure(
            f"browser evidence unreadable: {browser_path}: {exc}"
        ) from exc
    markers = {
        "real_keycloak_login": "After real Keycloak browser login" in browser_text,
        "authenticated_bff_facility": "Authenticated facility response" in browser_text,
        "playwright_result": "Playwright browser result" in browser_text,
        "visible_ui": "has_authenticated_actor=true" in browser_text
        and "has_lot=true" in browser_text,
    }
    return {
        "bff": {
            "authenticated_facility_evidence": "Authenticated facility response reported"
            in browser_text,
            "world_id": WORLD_ID if "world `DEMO-WORLD`" in browser_text else None,
            "source": "digital-twin-service"
            if "source `digital-twin-service`" in browser_text
            else None,
            "freshness": "FRESH" if "freshness `FRESH`" in browser_text else None,
        },
        "keycloak": {"health_status": keycloak_status},
        "ui": {"http_status": ui_status},
        "browser_evidence": {"path": str(browser_path), "markers": markers},
    }


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _manifest_base(scenario_id: str, run_id: str, scope: str) -> dict[str, Any]:
    return {
        "schema": "cap.wp-core-008.av-scenario/v1",
        "scenario_id": scenario_id,
        "run_id": run_id,
        "source_main_sha": MAIN_SHA,
        "world_id": WORLD_ID,
        "branch_id": BRANCH_ID,
        "runtime_mode": "REAL",
        "mocked_boundaries": [],
        "scope": scope,
    }


def run_av01(run_id: str, browser_path: Path) -> dict[str, Any]:
    lot_id = f"AV-SCEN-01-{run_id}"
    command_id = uuid5(NAMESPACE_URL, f"wp-core-008/{run_id}/command")
    hold_id = uuid5(NAMESPACE_URL, f"wp-core-008/{run_id}/hold")
    correlation_id = f"wp-core-008-av01-{run_id}"
    revision = f"av01-{run_id}-initial"
    _seed_lot(lot_id, revision)
    with _connect(_core_dsn()) as connection:
        before = _state(connection, lot_id)
    if before is None:
        raise ScenarioFailure("AV-SCEN-01 setup lot is not readable through Core role")
    status, raw = _http(
        "http://127.0.0.1:28081/v1/commands",
        method="POST",
        body={
            "command_type": "PlaceLotOnHold",
            "command_version": 1,
            "command_id": str(command_id),
            "idempotency_key": f"wp-core-008-av01-{run_id}",
            "world_id": WORLD_ID,
            "correlation_id": correlation_id,
            "target": {"entity_type": "Lot", "entity_id": lot_id},
            "expected": {"expected_revision": revision},
            "hold_reason": "inspection-triggered controlled recovery acceptance slice",
            "material_hold_id": str(hold_id),
        },
    )
    if status != 200:
        raise ScenarioFailure(
            f"Core command rejected at HTTP boundary: status={status}"
        )
    response = _json_body(raw, "Core command")
    if response.get("status") != "ACCEPTED" or response.get("command_id") != str(
        command_id
    ):
        raise ScenarioFailure(
            "Core command did not return the expected accepted identity"
        )
    event_id = str(response.get("event_id") or "")
    if not event_id:
        raise ScenarioFailure("Core accepted command without EventID")
    reached = _wait_for_rows(lot_id, event_id)
    with _connect(_core_dsn()) as connection:
        after = _state(connection, lot_id)
        outcome = connection.execute(
            "SELECT outcome_id, command_id, status, world_id, correlation_id, "
            "effect_verification, error_code FROM core.command_outcome WHERE command_id=%s",
            (str(command_id),),
        ).fetchone()
    surfaces = _surface_checks(browser_path)
    outbox = reached["outbox"]
    event = outbox["event"]
    checks = [
        _check(
            "core_mutation",
            bool(before["held"] is False and after and after["held"] is True),
            "lot hold changed false -> true",
        ),
        _check(
            "command_outcome",
            outcome is not None and outcome["status"] == "ACCEPTED",
            "durable accepted command outcome",
        ),
        _check(
            "transactional_outbox",
            outbox["publication_status"] == "PUBLISHED",
            "published outbox row",
        ),
        _check(
            "event_identity",
            outbox["event_id"] == event_id
            and outbox["causation_id"] == str(command_id),
            "EventID and causation bind to command",
        ),
        _check(
            "correlation",
            outbox["correlation_id"] == correlation_id,
            "correlation propagated to outbox",
        ),
        _check(
            "twin_projection",
            reached["twin_projection"]["source_event_id"] == event_id,
            "Twin source EventID matches outbox",
        ),
        _check(
            "nats_delivery",
            reached["twin_applied_event"]["event_id"] == event_id,
            "Twin consumer ledger records delivery",
        ),
        _check(
            "keycloak_and_ui",
            surfaces["keycloak"]["health_status"] == 200
            and surfaces["ui"]["http_status"] == 200,
            "Keycloak health and UI HTTP surface",
        ),
        _check(
            "bff_response",
            bool(
                surfaces["bff"]["authenticated_facility_evidence"]
                and surfaces["bff"]["world_id"] == WORLD_ID
                and surfaces["bff"]["source"] == "digital-twin-service"
                and surfaces["bff"]["freshness"] == "FRESH"
            ),
            "authenticated BFF facility response is bound",
        ),
        _check(
            "browser_acceptance_reference",
            all(surfaces["browser_evidence"]["markers"].values()),
            "real authenticated browser evidence is bound",
        ),
    ]
    manifest = _manifest_base(
        "AV-SCEN-01",
        run_id,
        "WP-CORE-008 Core/outbox/JetStream/Twin/BFF/UI acceptance slice; not the full Vision/RCA/Scheduler/Automation portfolio",
    )
    manifest.update(
        {
            "trigger_boundary": "Core PlaceLotOnHold acceptance slice; no Vision/RCA claim",
            "command": {
                "id": str(command_id),
                "response": response,
                "outcome": None if outcome is None else dict(outcome),
            },
            "core_before": before,
            "core_after": after,
            "outbox": {key: value for key, value in outbox.items() if key != "event"},
            "event": {
                key: event.get(key)
                for key in (
                    "event_id",
                    "event_type",
                    "world_id",
                    "correlation_id",
                    "causation_id",
                    "trace_id",
                )
            },
            "twin": reached,
            "nats": asyncio.run(_nats_info()),
            "surfaces": surfaces,
            "checks": checks,
            "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        }
    )
    return manifest


def _dispatch_values(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    patterns = {
        "lot_id": r"Open lot: `([^`]+)`",
        "command_id": r"Legal dispatch command: `([^`]+)`",
        "event_id": r"\| dispatch \| `[^`]+` \| `([^`]+)`",
        "correlation_id": r"CorrelationID: `([^`]+)`",
    }
    values: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match is None:
            raise ScenarioFailure(f"dispatch evidence missing {key}: {path}")
        values[key] = match.group(1)
    return values


def run_av03(run_id: str, browser_path: Path, dispatch_path: Path) -> dict[str, Any]:
    values = _dispatch_values(dispatch_path)
    with _connect(_core_dsn()) as core:
        state = _state(core, values["lot_id"])
        outcome = core.execute(
            "SELECT outcome_id, command_id, status, world_id, correlation_id, "
            "effect_verification, error_code FROM core.command_outcome WHERE command_id=%s",
            (values["command_id"],),
        ).fetchone()
        outbox = core.execute(
            "SELECT outbox_id, event_id, event_type, aggregate_id, aggregate_version, "
            "world_id, correlation_id, causation_id, publication_status, event "
            "FROM core.outbox WHERE event_id=%s",
            (values["event_id"],),
        ).fetchone()
    with _connect(_twin_dsn()) as twin:
        projection = twin.execute(
            "SELECT aggregate_id, world_id, branch_id, aggregate_version, state, "
            "source_event_id, source_revision FROM twin.projection_entity "
            "WHERE aggregate_id=%s AND world_id=%s AND branch_id=%s",
            (values["lot_id"], WORLD_ID, BRANCH_ID),
        ).fetchone()
        applied = twin.execute(
            "SELECT consumer_scope, event_id, world_id, branch_id, aggregate_id, aggregate_version "
            "FROM twin.applied_event WHERE event_id=%s AND consumer_scope=%s",
            (values["event_id"], CONSUMER_SCOPE),
        ).fetchone()
    if (
        state is None
        or outcome is None
        or outbox is None
        or projection is None
        or applied is None
    ):
        raise ScenarioFailure(
            "AV-SCEN-03 current-main dispatch evidence is no longer present"
        )
    surfaces = _surface_checks(browser_path)
    event = outbox["event"]
    checks = [
        _check(
            "normal_production_state",
            state["execution_state"] == "DISPATCHED" and state["held"] is False,
            "dispatch completed without active hold",
        ),
        _check(
            "accepted_dispatch",
            outcome["status"] == "ACCEPTED"
            and str(outcome["command_id"]) == values["command_id"],
            "legal dispatch outcome remains accepted",
        ),
        _check(
            "dispatch_event",
            outbox["event_id"] == values["event_id"]
            and outbox["event_type"] == "production.lot-dispatch-authorized",
            "dispatch event is the observed effect",
        ),
        _check(
            "no_false_recovery",
            event.get("event_type") != "production.lot-held",
            "normal path has no hold/recovery event",
        ),
        _check(
            "twin_projection",
            projection["source_event_id"] == values["event_id"]
            and projection["state"].get("dispatchable") is True,
            "Twin reflects normal dispatch",
        ),
        _check(
            "nats_delivery",
            applied["event_id"] == values["event_id"],
            "Twin consumer ledger records dispatch delivery",
        ),
        _check(
            "keycloak_and_ui",
            surfaces["keycloak"]["health_status"] == 200
            and surfaces["ui"]["http_status"] == 200,
            "Keycloak health and UI HTTP surface",
        ),
        _check(
            "bff_response",
            bool(
                surfaces["bff"]["authenticated_facility_evidence"]
                and surfaces["bff"]["world_id"] == WORLD_ID
                and surfaces["bff"]["source"] == "digital-twin-service"
                and surfaces["bff"]["freshness"] == "FRESH"
            ),
            "authenticated BFF facility response is bound",
        ),
        _check(
            "browser_acceptance_reference",
            all(surfaces["browser_evidence"]["markers"].values()),
            "real authenticated browser evidence is bound",
        ),
    ]
    manifest = _manifest_base(
        "AV-SCEN-03",
        run_id,
        "WP-CORE-008 normal-production/no-false-recovery observation over the merged dispatch runtime; not the full architecture portfolio",
    )
    manifest.update(
        {
            "source_evidence": str(dispatch_path),
            "observed_only": True,
            "command": {"id": values["command_id"], "outcome": dict(outcome)},
            "core_after": state,
            "outbox": {key: value for key, value in outbox.items() if key != "event"},
            "event": {
                key: event.get(key)
                for key in (
                    "event_id",
                    "event_type",
                    "world_id",
                    "correlation_id",
                    "causation_id",
                    "trace_id",
                )
            },
            "twin": {"projection": dict(projection), "applied_event": dict(applied)},
            "nats": asyncio.run(_nats_info()),
            "surfaces": surfaces,
            "checks": checks,
            "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        }
    )
    return manifest


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def _failure_payload(scenario_id: str, run_id: str, error: str) -> dict[str, Any]:
    return {
        "schema": "cap.wp-core-008.av-scenario/v1",
        "scenario_id": scenario_id,
        "run_id": run_id,
        "source_main_sha": MAIN_SHA,
        "status": "FAIL",
        "runtime_mode": "REAL",
        "error": error,
        "checks": [{"name": "scenario_execution", "passed": False, "detail": error}],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=("AV-SCEN-01", "AV-SCEN-03"))
    parser.add_argument(
        "--run-id",
        required=True,
        help="unique run identity; reuse fails closed if setup already exists",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--browser-evidence", type=Path, default=Path(DEFAULT_BROWSER_EVIDENCE)
    )
    parser.add_argument(
        "--dispatch-evidence", type=Path, default=Path(DEFAULT_DISPATCH_EVIDENCE)
    )
    args = parser.parse_args(argv)
    try:
        if args.scenario == "AV-SCEN-01":
            payload = run_av01(args.run_id, args.browser_evidence)
        else:
            payload = run_av03(
                args.run_id, args.browser_evidence, args.dispatch_evidence
            )
    except Exception as exc:
        payload = _failure_payload(args.scenario, args.run_id, str(exc))
        _write_json(args.output, payload)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    _write_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
