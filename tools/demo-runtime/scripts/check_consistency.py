#!/usr/bin/env python3
"""Fail-closed machine-readable Core/Twin/runtime evidence consistency check."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def check(payload: dict[str, Any]) -> dict[str, Any]:
    command = payload.get("command") or {}
    response = command.get("response") or {}
    outcome = command.get("outcome") or {}
    outbox = payload.get("outbox") or {}
    event = payload.get("event") or {}
    twin = payload.get("twin") or {}
    projection = twin.get("twin_projection") or twin.get("projection") or {}
    applied = twin.get("twin_applied_event") or twin.get("applied_event") or {}
    twin_revision = twin.get("twin_revision") or {}
    nats = payload.get("nats") or {}
    surfaces = payload.get("surfaces") or {}
    bff = surfaces.get("bff") or {}
    browser = (surfaces.get("browser_evidence") or {}).get("markers") or {}
    command_id = str(command.get("id") or response.get("command_id") or "")
    event_id = str(event.get("event_id") or outbox.get("event_id") or "")
    checks = [
        _check(
            "world_identity",
            payload.get("world_id")
            == outbox.get("world_id")
            == event.get("world_id")
            == projection.get("world_id"),
            "WorldID is stable across manifest, outbox, event and Twin",
        ),
        _check(
            "command_identity",
            bool(
                command_id
                and response.get("command_id", command_id) == command_id
                and (outcome.get("command_id", command_id) == command_id)
            ),
            "CommandID binds response and durable outcome",
        ),
        _check(
            "event_identity",
            bool(
                event_id
                and outbox.get("event_id") == event_id
                and applied.get("event_id") == event_id
                and projection.get("source_event_id") == event_id
            ),
            "EventID binds outbox, delivery ledger and projection",
        ),
        _check(
            "causation",
            outbox.get("causation_id") == command_id
            or event.get("causation_id") == command_id,
            "causation points to CommandID",
        ),
        _check(
            "correlation",
            outbox.get("correlation_id")
            == event.get("correlation_id")
            == outcome.get("correlation_id", outbox.get("correlation_id")),
            "correlation is preserved",
        ),
        _check(
            "revisions",
            bool(outbox.get("aggregate_version"))
            and bool(projection.get("aggregate_version"))
            and bool(projection.get("source_revision")),
            "aggregate and source revisions are present",
        ),
        _check(
            "outbox_published",
            outbox.get("publication_status") == "PUBLISHED",
            "transactional outbox was published",
        ),
        _check(
            "nats_consumer",
            nats.get("stream") == "CAP_EVENTS"
            and nats.get("durable") == "twin-primary"
            and nats.get("num_ack_pending") == 0,
            "JetStream stream/durable consumer delivered without pending ACK",
        ),
        _check(
            "twin_applied",
            applied.get("consumer_scope") == "twin-primary"
            and applied.get("event_id") == event_id,
            "real Twin consumer ledger contains EventID",
        ),
        _check(
            "twin_fresh",
            twin_revision.get("status") in {"FRESH", None}
            and projection.get("source_event_id") == event_id,
            "Twin projection is fresh for the event",
        ),
        _check(
            "keycloak_ui",
            (surfaces.get("keycloak") or {}).get("health_status") == 200
            and (surfaces.get("ui") or {}).get("http_status") == 200,
            "Keycloak health and UI HTTP result are successful",
        ),
        _check(
            "bff_response",
            bool(
                bff.get("authenticated_facility_evidence") is True
                and bff.get("world_id") == payload.get("world_id")
                and bff.get("source") == "digital-twin-service"
                and bff.get("freshness") == "FRESH"
            ),
            "authenticated BFF facility result is bound",
        ),
        _check(
            "browser_visible",
            all(
                browser.get(key) is True
                for key in (
                    "real_keycloak_login",
                    "authenticated_bff_facility",
                    "playwright_result",
                    "visible_ui",
                )
            ),
            "authenticated browser/UI acceptance is referenced",
        ),
    ]
    result = {
        "schema": "cap.wp-core-008.consistency/v1",
        "scenario_id": payload.get("scenario_id"),
        "run_id": payload.get("run_id"),
        "source_main_sha": payload.get("source_main_sha"),
        "status": "PASS" if all(item["passed"] for item in checks) else "FAIL",
        "checks": checks,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = check(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
