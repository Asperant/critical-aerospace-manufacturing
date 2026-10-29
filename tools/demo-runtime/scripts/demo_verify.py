#!/usr/bin/env python3
"""Verify and capture the complete live demo chain from current runtime state."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cap_demo_runtime.av_scenarios import _connect, _nats_info, _state


def _http_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError:
        return 0


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def verify(artifact_dir: Path) -> dict[str, Any]:
    context = json.loads(
        (artifact_dir / "scenario-context.json").read_text(encoding="utf-8")
    )
    browser_path = artifact_dir / "browser-result.json"
    browser = (
        json.loads(browser_path.read_text(encoding="utf-8"))
        if browser_path.exists()
        else {}
    )
    command = context.get("command", {})
    response = command.get("response", {})
    outcome = command.get("outcome", {})
    event_id = str(
        context.get("event", {}).get("event_id") or response.get("event_id") or ""
    )
    lot_id = str(context.get("lot_id", "DEMO-LOT-001"))
    core_dsn = os.environ.get("CAP_AV_CORE_DSN") or _core_dsn()
    twin_dsn = os.environ.get("CAP_AV_TWIN_DSN") or _twin_dsn()
    with _connect(core_dsn) as core:
        core_state = _state(core, lot_id)
        outbox = core.execute(
            "SELECT outbox_id, event_id, event_type, aggregate_id, aggregate_version, "
            "world_id, correlation_id, causation_id, publication_status, event "
            "FROM core.outbox WHERE event_id=%s",
            (event_id,),
        ).fetchone()
    with _connect(twin_dsn) as twin:
        applied = twin.execute(
            "SELECT consumer_scope, event_id, world_id, branch_id, aggregate_id, aggregate_version "
            "FROM twin.applied_event WHERE event_id=%s AND consumer_scope='twin-primary'",
            (event_id,),
        ).fetchone()
        projection = twin.execute(
            "SELECT aggregate_id, world_id, branch_id, aggregate_version, state, source_event_id, source_revision "
            "FROM twin.projection_entity WHERE aggregate_id=%s AND world_id='DEMO-WORLD' AND branch_id='PRIMARY'",
            (lot_id,),
        ).fetchone()
        revision = twin.execute(
            "SELECT source_event_id, status FROM twin.projection_revision "
            "WHERE world_id='DEMO-WORLD' AND branch_id='PRIMARY'",
        ).fetchone()
    nats = asyncio.run(_nats_info())
    keycloak = _http_status(
        f"http://127.0.0.1:{os.environ.get('CAP_KEYCLOAK_PORT', '28080')}/realms/cap-platform"
    )
    ui = _http_status(f"http://127.0.0.1:{os.environ.get('CAP_UI_PORT', '29080')}/")
    projection_dict = None if projection is None else dict(projection)
    applied_dict = None if applied is None else dict(applied)
    outbox_dict = (
        None
        if outbox is None
        else {key: value for key, value in dict(outbox).items() if key != "event"}
    )
    browser_markers = {
        key: browser.get(key) is True
        for key in (
            "has_authenticated_actor",
            "has_lot",
            "has_held_state",
            "has_active_hold",
            "has_quality_excursion",
            "bff_authenticated",
            "showcase_authenticated",
            "has_timeline",
            "has_dispatch_blocked",
        )
    }
    simulator = context.get("simulator", {})
    dispatch = context.get("dispatch", {}).get("response", {})
    checks = [
        _check(
            "world_identity",
            bool(
                context.get("world_id") == "DEMO-WORLD"
                and outbox_dict
                and outbox_dict["world_id"] == "DEMO-WORLD"
            ),
            "WorldID is stable",
        ),
        _check(
            "command_identity",
            bool(
                command.get("id")
                and response.get("command_id") == command["id"]
                and outcome.get("command_id") == command["id"]
            ),
            "CommandID binds response and durable outcome",
        ),
        _check(
            "simulator_trigger",
            simulator.get("event", {}).get("event_type") == "INSPECTION_FAILED"
            and simulator.get("event", {}).get("provenance") == "SIMULATION"
            and bool(simulator.get("event_sequence_digest")),
            "deterministic simulator trigger and replay identity are present",
        ),
        _check(
            "postgres_state",
            core_state is not None and core_state["held"] is True,
            "Core PostgreSQL lot is HELD",
        ),
        _check(
            "outbox_published",
            outbox_dict is not None
            and outbox_dict["publication_status"] == "PUBLISHED",
            "outbox row is PUBLISHED",
        ),
        _check(
            "event_identity",
            bool(
                event_id
                and outbox_dict
                and outbox_dict["event_id"] == event_id
                and applied_dict
                and applied_dict["event_id"] == event_id
                and projection_dict
                and projection_dict["source_event_id"] == event_id
            ),
            "EventID binds outbox, ledger and projection",
        ),
        _check(
            "nats_consumer",
            nats.get("stream") == "CAP_EVENTS"
            and nats.get("durable") == "twin-primary"
            and nats.get("num_ack_pending") == 0,
            "JetStream consumer has no pending ACK",
        ),
        _check(
            "twin_fresh",
            revision is not None and revision["status"] == "FRESH",
            "Twin projection revision is FRESH",
        ),
        _check(
            "dispatch_active_hold",
            dispatch.get("status") == "REJECTED"
            and dispatch.get("error_code") == "ACTIVE_HOLD",
            "dispatch attempt is durably rejected with ACTIVE_HOLD",
        ),
        _check(
            "keycloak_ui",
            keycloak == 200 and ui == 200,
            "Keycloak realm and UI answer HTTP 200",
        ),
        _check(
            "browser_visible",
            all(browser_markers.values()),
            "authenticated browser result is present",
        ),
    ]
    payload = {
        "schema": "cap.wp-doc-004.demo-verification/v1",
        "source_main_sha": os.environ.get(
            "CAP_DEMO_SOURCE_SHA", context.get("source_main_sha")
        ),
        "runtime_mode": "REAL",
        "world_id": "DEMO-WORLD",
        "branch_id": "PRIMARY",
        "lot_id": lot_id,
        "command": command,
        "core_before": context.get("core_before"),
        "core_after": None if core_state is None else dict(core_state),
        "outbox": outbox_dict,
        "event": context.get("event"),
        "simulator": simulator,
        "dispatch": context.get("dispatch"),
        "twin": {
            "projection": projection_dict,
            "applied_event": applied_dict,
            "projection_revision": None if revision is None else dict(revision),
        },
        "nats": nats,
        "surfaces": {
            "keycloak": {"health_status": keycloak},
            "ui": {"http_status": ui},
            "bff": {
                "authenticated_facility_evidence": browser.get("bff_authenticated")
                is True,
                "world_id": browser.get("world_id"),
                "source": "digital-twin-service"
                if browser.get("bff_authenticated")
                else None,
                "freshness": "FRESH" if browser.get("bff_authenticated") else None,
            },
            "browser_evidence": {
                "path": str(browser_path),
                "markers": {
                    "real_keycloak_login": browser.get("has_authenticated_actor")
                    is True,
                    "authenticated_bff_facility": browser.get("bff_authenticated")
                    is True,
                    "playwright_result": browser.get("status") == "PASS",
                    "visible_ui": browser.get("has_lot") is True
                    and browser.get("has_held_state") is True,
                },
            },
        },
        "checks": checks,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "note": "Core command acceptance remains distinct from downstream effect verification; the latter is evidenced by the real Twin projection and browser result.",
    }
    return payload


def _core_dsn() -> str:
    from cap_demo_runtime.av_scenarios import _core_dsn as runtime_core_dsn

    return runtime_core_dsn()


def _twin_dsn() -> str:
    from cap_demo_runtime.av_scenarios import _twin_dsn as runtime_twin_dsn

    return runtime_twin_dsn()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = verify(args.artifact_dir)
    except Exception as exc:
        payload = {
            "schema": "cap.wp-doc-004.demo-verification/v1",
            "status": "FAIL",
            "error": str(exc),
            "checks": [
                {"name": "verification_execution", "passed": False, "detail": str(exc)}
            ],
        }
    output = args.artifact_dir / "latest.json"
    output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    lines = [
        "DEMO VERIFICATION",
        "-----------------",
        "CHECK                       RESULT  DETAIL",
    ]
    for item in payload.get("checks", []):
        lines.append(
            f"{item['name']:<27} {'PASS' if item['passed'] else 'FAIL':<7} {item['detail']}"
        )
    lines.append(f"OVERALL                     {payload['status']}")
    text = "\n".join(lines) + "\n"
    (args.artifact_dir / "verification.txt").write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
