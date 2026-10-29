#!/usr/bin/env python3
"""Run the deterministic WP-DOC-004 hold scenario through the real Core API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from cap_demo_runtime.av_scenarios import (
    BRANCH_ID,
    CONSUMER_SCOPE,
    WORLD_ID,
    ScenarioFailure,
    _connect,
    _http,
    _json_body,
    _nats_info,
    _state,
    _wait_for_rows,
)

LOT_ID = "DEMO-LOT-001"
CORRELATION_ID = "wp-doc-004-demo-hold"
COMMAND_ID = str(uuid5(NAMESPACE_URL, "cap-demo/WP-DOC-004/DEMO-LOT-001/hold"))
HOLD_ID = str(uuid5(NAMESPACE_URL, "cap-demo/WP-DOC-004/DEMO-LOT-001/material-hold"))


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def run() -> dict[str, Any]:
    with _connect(os.environ.get("CAP_AV_CORE_DSN") or _core_dsn()) as connection:
        before = _state(connection, LOT_ID)
    if before is None:
        raise ScenarioFailure(f"seeded demo lot is missing: {LOT_ID}")
    if before["held"]:
        raise ScenarioFailure(
            "demo lot is already held; run './tools/demo-runtime/demo.sh reset' first"
        )

    status, raw = _http(
        f"http://127.0.0.1:{os.environ.get('CAP_CORE_PORT', '28081')}/v1/commands",
        method="POST",
        body={
            "command_type": "PlaceLotOnHold",
            "command_version": 1,
            "command_id": COMMAND_ID,
            "idempotency_key": CORRELATION_ID,
            "world_id": WORLD_ID,
            "correlation_id": CORRELATION_ID,
            "target": {"entity_type": "Lot", "entity_id": LOT_ID},
            "expected": {"expected_revision": before["revision"]},
            "hold_reason": "inspection-triggered controlled recovery acceptance slice",
            "material_hold_id": HOLD_ID,
        },
    )
    if status != 200:
        raise ScenarioFailure(
            f"Core command rejected at HTTP boundary: status={status}"
        )
    response = _json_body(raw, "Core command")
    if response.get("status") != "ACCEPTED" or response.get("command_id") != COMMAND_ID:
        raise ScenarioFailure(
            "Core command did not return the expected accepted identity"
        )
    event_id = str(response.get("event_id") or "")
    if not event_id:
        raise ScenarioFailure("Core accepted command without EventID")

    reached = _wait_for_rows(LOT_ID, event_id)
    with _connect(os.environ.get("CAP_AV_CORE_DSN") or _core_dsn()) as connection:
        after = _state(connection, LOT_ID)
        outcome = connection.execute(
            "SELECT outcome_id, command_id, status, world_id, correlation_id, "
            "effect_verification, error_code FROM core.command_outcome WHERE command_id=%s",
            (COMMAND_ID,),
        ).fetchone()
    if after is None or outcome is None:
        raise ScenarioFailure("Core mutation did not leave a durable state/outcome")

    outbox = reached["outbox"]
    event = outbox["event"]
    checks = [
        _check(
            "core_mutation",
            before["held"] is False and after["held"] is True,
            "false -> true hold state",
        ),
        _check(
            "command_outcome",
            outcome["status"] == "ACCEPTED",
            "durable accepted Core outcome",
        ),
        _check(
            "transactional_outbox",
            outbox["publication_status"] == "PUBLISHED",
            "published outbox row",
        ),
        _check(
            "event_identity",
            outbox["event_id"] == event_id and outbox["causation_id"] == COMMAND_ID,
            "EventID and causation bind to CommandID",
        ),
        _check(
            "twin_projection",
            reached["twin_projection"]["source_event_id"] == event_id,
            "Twin source EventID matches",
        ),
        _check(
            "nats_delivery",
            reached["twin_applied_event"]["event_id"] == event_id,
            "Twin ledger contains EventID",
        ),
        _check(
            "twin_fresh",
            reached["twin_revision"] is not None
            and reached["twin_revision"]["status"] == "FRESH",
            "Twin projection revision is FRESH",
        ),
    ]
    return {
        "schema": "cap.wp-doc-004.demo-context/v1",
        "source_main_sha": os.environ.get("CAP_DEMO_SOURCE_SHA", "unknown"),
        "runtime_mode": "REAL",
        "world_id": WORLD_ID,
        "branch_id": BRANCH_ID,
        "lot_id": LOT_ID,
        "consumer_scope": CONSUMER_SCOPE,
        "command": {"id": COMMAND_ID, "response": response, "outcome": dict(outcome)},
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
        "nats": __import__("asyncio").run(_nats_info()),
        "checks": checks,
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
    }


def _core_dsn() -> str:
    from cap_demo_runtime.av_scenarios import _core_dsn as runtime_core_dsn

    return runtime_core_dsn()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = run()
    except Exception as exc:
        payload = {
            "schema": "cap.wp-doc-004.demo-context/v1",
            "source_main_sha": os.environ.get("CAP_DEMO_SOURCE_SHA", "unknown"),
            "runtime_mode": "REAL",
            "status": "FAIL",
            "error": str(exc),
            "checks": [
                {"name": "scenario_execution", "passed": False, "detail": str(exc)}
            ],
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    for item in payload.get("checks", []):
        print(
            f"{'PASS' if item['passed'] else 'FAIL'}  {item['name']}: {item['detail']}"
        )
    if payload["status"] != "PASS":
        print(
            f"FAIL  scenario: {payload.get('error', 'scenario checks failed')}",
            file=sys.stderr,
        )
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
