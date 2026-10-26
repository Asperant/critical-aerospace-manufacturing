from __future__ import annotations

import pytest
from operational_twin import (
    ProjectionEvent,
    ProjectionGap,
    ProjectionOrderError,
    ProjectionState,
    Projector,
)
from operational_twin.nats_consumer import apply_delivery, consumer_configuration


def event(
    event_id: str,
    version: int,
    event_type: str = "production.lot-held",
    *,
    world: str = "PRIMARY",
    branch: str = "PRIMARY",
    aggregate_id: str = "LOT-1",
) -> ProjectionEvent:
    return ProjectionEvent(
        event_id,
        event_type,
        world,
        "Lot",
        aggregate_id,
        version,
        {
            "event_type": event_type,
            "aggregate_type": "Lot",
            "aggregate_id": aggregate_id,
            "aggregate_version": version,
            "material_hold_id": "H-1",
            "reason": "quality",
        },
        branch,
    )


def test_production_projection_is_traceable_and_read_only() -> None:
    projector = Projector(ProjectionState("PRIMARY"))
    result = projector.apply(event("E-1", 1))
    assert result.outcome == "PROCESSED"
    query = projector.query("Lot", "LOT-1")
    assert query is not None
    assert query["source_event_id"] == "E-1"
    assert projector.health()["source_revision"] == "E-1"
    assert not hasattr(projector, "mutate")


def test_duplicate_is_idempotent() -> None:
    projector = Projector(ProjectionState("PRIMARY"))
    projector.apply(event("E-1", 1))
    assert projector.apply(event("E-1", 1)).outcome == "DUPLICATE"
    assert len(projector.state.entities) == 1


def test_old_and_gap_events_fail_closed_and_gap_marks_stale() -> None:
    projector = Projector(ProjectionState("PRIMARY"))
    projector.apply(event("E-1", 1))
    with pytest.raises(ProjectionOrderError):
        projector.apply(event("E-0", 1))
    with pytest.raises(ProjectionGap):
        projector.apply(event("E-3", 3))
    assert projector.health()["status"] == "STALE"


def test_world_and_branch_are_admitted_explicitly() -> None:
    projector = Projector(ProjectionState("PRIMARY", "SIM-A"))
    with pytest.raises(ValueError, match="scope"):
        projector.apply(event("E-1", 1, world="OTHER", branch="SIM-A"))
    with pytest.raises(ValueError, match="scope"):
        projector.apply(event("E-1", 1, branch="PRIMARY"))


def test_all_supported_namespaces_have_handlers() -> None:
    projector = Projector(ProjectionState("PRIMARY"))
    for index, event_type in enumerate(
        ("equipment.machine-failed", "quality.inspection-result"), start=1
    ):
        result = projector.apply(
            event(f"E-{index}", 1, event_type, aggregate_id=f"ENTITY-{index}")
        )
        assert result.outcome == "PROCESSED"


def test_evt002_decode_and_evt003_binding_are_explicit() -> None:
    import json

    payload = event("E-1", 1).payload
    wire = {
        "envelope": {
            "event_id": "E-1",
            "event_type": payload["event_type"],
            "schema_version": 1,
            "producer": "manufacturing-core",
            "world_id": "PRIMARY",
            "correlation_id": "C-1",
            "causation_id": None,
            "trace_id": "T-1",
            "occurred_at": {"clock": "UTC", "value": "2026-01-01T00:00:00Z"},
            "observed_at": "2026-01-01T00:00:01Z",
            "entity_refs": [{"entity_type": "Lot", "id": "LOT-1", "revision": "1"}],
        },
        "payload": payload,
    }
    result = apply_delivery(
        Projector(ProjectionState("PRIMARY")),
        json.dumps(wire).encode(),
        expected_world_id="PRIMARY",
    )
    assert result.outcome == "PROCESSED"
    assert (
        consumer_configuration(
            stream="EVENTS",
            subject="events.>",
            durable="twin-live-v1",
            ack_wait_seconds=5,
            max_deliver=5,
        )["deliver_policy"]
        == "all"
    )


def test_invalid_world_is_rejected_before_effect() -> None:
    import json

    payload = event("E-1", 1).payload
    wire = {
        "envelope": {
            "event_id": "E-1",
            "event_type": payload["event_type"],
            "schema_version": 1,
            "producer": "manufacturing-core",
            "world_id": "OTHER",
            "correlation_id": "C-1",
            "causation_id": None,
            "trace_id": "T-1",
            "occurred_at": {"clock": "UTC", "value": "2026-01-01T00:00:00Z"},
            "observed_at": "2026-01-01T00:00:01Z",
            "entity_refs": [{"entity_type": "Lot", "id": "LOT-1", "revision": "1"}],
        },
        "payload": payload,
    }
    with pytest.raises(ValueError, match="world_id"):
        apply_delivery(
            Projector(ProjectionState("PRIMARY")),
            json.dumps(wire).encode(),
            expected_world_id="PRIMARY",
        )
