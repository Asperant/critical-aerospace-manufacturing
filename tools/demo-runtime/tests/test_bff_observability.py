from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[3] / "services/operations-bff/src"),
)

from cap_demo_runtime import bff  # noqa: E402
from cap_demo_runtime.config import Settings  # noqa: E402


class _Result:
    def __init__(self, row: dict[str, Any]) -> None:
        self.row = row

    def fetchone(self) -> dict[str, Any]:
        return self.row


class _Connection:
    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, query: str, _params: object = ()) -> _Result:
        if query == "SELECT 1":
            return _Result({"?column?": 1})
        return _Result({"count": 7})


def test_system_observability_exposes_runtime_facts_and_unknowns(
    monkeypatch: Any,
) -> None:
    settings = Settings(
        pg_dsn="postgresql://demo.invalid/cap",
        world_id="DEMO-WORLD",
    )
    monkeypatch.setattr(bff, "_connection", lambda _settings: _Connection())
    monkeypatch.setattr(
        bff,
        "_jetstream_health_sync",
        lambda _settings: {
            "status": "UP",
            "detail": "CAP_EVENTS/twin-primary connected",
            "messages": 12,
            "consumer": "twin-primary",
        },
    )
    monkeypatch.setattr(
        bff,
        "_http_health",
        lambda _url: {"status": "UP", "detail": "HTTP 200"},
    )

    result = bff._system_observability(
        settings,
        "DEMO-WORLD",
        "DEMO-LOT-001",
        {
            "hold_command": {
                "command_id": "CMD-1",
                "causation_id": "SIM-1",
            },
            "outbox": {
                "outbox_id": "OB-1",
                "event_id": "EV-1",
                "publication_status": "PUBLISHED",
            },
            "dispatch_attempt": None,
            "observability": {
                "commands": 3,
                "published_events": 2,
                "active_holds": 1,
            },
        },
        {"event_id": "EV-1"},
        {"source_event_id": "EV-1", "status": "FRESH"},
    )

    assert [item["label"] for item in result["architecture"]] == [
        "Simulator",
        "Core",
        "PostgreSQL",
        "Transactional Outbox",
        "NATS / JetStream",
        "Digital Twin",
        "BFF",
    ]
    assert result["architecture"][3]["status"] == "PUBLISHED"
    assert result["architecture"][5]["status"] == "UPDATED"
    assert result["counters"][:3] == [
        {"id": "commands", "label": "Commands observed", "value": 3},
        {"id": "published-events", "label": "Events published", "value": 2},
        {"id": "twin-updates", "label": "Twin updates", "value": 7},
    ]
    assert result["world_id"] == "DEMO-WORLD"
    assert result["selected_lot"] == "DEMO-LOT-001"
    assert all(item["status"] == "UP" for item in result["health"])
