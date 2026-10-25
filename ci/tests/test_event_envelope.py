"""TEST-EVT-002-001: TEST-EVT-ENVELOPE / TEST-DATA-TIME, isolated unit fixtures.

Metadata foundation only; no service trace propagation or REAL acceptance claim.
"""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from cap_contracts import (
    CausationID,
    CorrelationID,
    EntityID,
    EntityReference,
    EntityRevision,
    EnvelopeError,
    EventEnvelope,
    SimulationTime,
    TraceID,
    new_event_id,
)

WALL_TIME = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


def envelope() -> EventEnvelope:
    return EventEnvelope(
        event_id=new_event_id(),
        event_type="production.example",
        schema_version=1,
        producer="manufacturing-core",
        world_id="what-if-world",
        correlation_id=CorrelationID("incident-chain"),
        causation_id=CausationID("direct-predecessor"),
        trace_id=TraceID("processing-trace"),
        occurred_at=SimulationTime(42.5, "run-1"),
        observed_at=WALL_TIME,
        entity_refs=(
            EntityReference("Lot", EntityID("lot-1"), EntityRevision("rev-A")),
        ),
    )


def test_valid_round_trip() -> None:
    original = envelope()
    assert EventEnvelope.from_mapping(original.to_mapping()) == original
    assert EventEnvelope.from_json(original.to_json()) == original
    assert EventEnvelope.from_json(original.to_json()).to_json() == original.to_json()
    assert original.entity_refs[0].revision == "rev-A"


def test_generated_event_id_and_replay_identity() -> None:
    ids = {new_event_id() for _ in range(100)}
    assert len(ids) == 100
    assert all(UUID(value).version == 4 for value in ids)
    original = envelope()
    replay = replace(original, trace_id=TraceID("new-replay-processing-trace"))
    assert replay.event_id == original.event_id
    assert replay.correlation_id == original.correlation_id
    assert replay.causation_id == original.causation_id
    assert replay.trace_id != original.trace_id


@pytest.mark.parametrize("root", [False, True])
def test_causal_and_trace_ids_preserved(root: bool) -> None:
    original = replace(envelope(), causation_id=None) if root else envelope()
    restored = EventEnvelope.from_json(original.to_json())
    assert restored.event_id == original.event_id
    assert restored.correlation_id == "incident-chain"
    assert restored.causation_id == (None if root else "direct-predecessor")
    assert restored.trace_id == "processing-trace"


@pytest.mark.parametrize("field", list(envelope().to_mapping()))
def test_missing_required_metadata_rejected(field: str) -> None:
    record = envelope().to_mapping()
    del record[field]
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_mapping(record)


@pytest.mark.parametrize(
    "field",
    ["event_id", "correlation_id", "causation_id", "trace_id", "world_id", "producer"],
)
@pytest.mark.parametrize("value", ["", " \t\n", 1, True, [], {}])
def test_malformed_identity_fields_rejected(field: str, value: object) -> None:
    record = envelope().to_mapping()
    record[field] = value
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_mapping(record)


@pytest.mark.parametrize(
    "field", ["event_id", "correlation_id", "trace_id", "world_id", "producer"]
)
def test_null_identity_rejected(field: str) -> None:
    record = envelope().to_mapping()
    record[field] = None
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_mapping(record)


@pytest.mark.parametrize("field", ["entity_type", "id", "revision"])
@pytest.mark.parametrize("value", [None, "", " \t", 0, True, [], {}])
def test_malformed_entity_reference_rejected(field: str, value: object) -> None:
    record: dict[str, object] = {
        "entity_type": "Lot",
        "id": "lot-1",
        "revision": "rev-A",
    }
    record[field] = value
    with pytest.raises(EnvelopeError):
        EntityReference.from_mapping(record)


@pytest.mark.parametrize("field", ["entity_type", "id", "revision"])
def test_missing_entity_reference_field_rejected(field: str) -> None:
    record = {"entity_type": "Lot", "id": "lot-1", "revision": "rev-A"}
    del record[field]
    with pytest.raises(EnvelopeError):
        EntityReference.from_mapping(record)


def test_published_core_opaque_id_revision_semantics() -> None:
    path = (
        Path(__file__).resolve().parents[2] / "services/manufacturing-core/contracts/v1"
    )
    for name in ("order-query.normal.json", "order-query.reentrant.json"):
        fixture: dict[str, Any] = json.loads((path / name).read_text())
        assert fixture["contract_version"] == "core.order-query.v1"
        references: list[tuple[str, dict[str, Any]]] = [
            ("ProductionOrder", fixture["order"]),
            ("ManufacturingRoute", fixture["route"]),
        ]
        for key, entity_type in (
            ("lots", "Lot"),
            ("components", "SerializedComponent"),
            ("equipment", "Equipment"),
        ):
            references.extend((entity_type, item) for item in fixture[key])
        references.extend(("RouteVisit", item) for item in fixture["route"]["visits"])
        for entity_type, item in references:
            ref = EntityReference.from_mapping(
                {
                    "entity_type": entity_type,
                    "id": item["id"],
                    "revision": item["revision"],
                }
            )
            restored = replace(envelope(), entity_refs=(ref,))
            assert EventEnvelope.from_json(restored.to_json()).entity_refs == (ref,)
            assert ref.id == item["id"] and ref.revision == item["revision"]


def test_explicit_utc_and_simulation_time_meanings() -> None:
    simulated = envelope()
    record = simulated.to_mapping()
    assert record["occurred_at"] == {
        "clock": "SIMULATION",
        "seconds": 42.5,
        "simulation_run_id": "run-1",
    }
    assert record["observed_at"] == "2026-10-25T12:00:00Z"
    utc = replace(simulated, occurred_at=WALL_TIME - timedelta(seconds=2))
    assert utc.to_mapping()["occurred_at"] == {
        "clock": "UTC",
        "value": "2026-10-25T11:59:58Z",
    }
    assert EventEnvelope.from_json(utc.to_json()) == utc
    assert EventEnvelope.from_json(simulated.to_json()).occurred_at == SimulationTime(
        42.5, "run-1"
    )


@pytest.mark.parametrize("field", ["occurred_at", "observed_at"])
@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 10, 25),
        datetime(2026, 10, 25, tzinfo=timezone(timedelta(hours=3))),
    ],
)
def test_non_utc_direct_timestamps_rejected(field: str, value: datetime) -> None:
    changes: dict[str, Any] = {field: value}
    with pytest.raises(EnvelopeError):
        replace(envelope(), **changes)


@pytest.mark.parametrize("value", [float("inf"), float("nan"), True, "42", None])
def test_invalid_simulation_time_rejected(value: Any) -> None:
    with pytest.raises(EnvelopeError):
        SimulationTime(value, "run-1")


@pytest.mark.parametrize(
    "occurrence",
    [
        "2026-10-25T12:00:00Z",
        {"clock": "LOCAL", "value": "2026-10-25T12:00:00"},
        {"clock": "UTC", "value": "2026-10-25T12:00:00"},
        {"clock": "SIMULATION", "seconds": 42},
        {"clock": "SIMULATION", "seconds": 42, "simulation_run_id": ""},
    ],
)
def test_ambiguous_occurrence_rejected(occurrence: object) -> None:
    record = envelope().to_mapping()
    record["occurred_at"] = occurrence
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_mapping(record)


@pytest.mark.parametrize("value", [True, 0, -1, "1", None])
def test_malformed_schema_version_rejected(value: object) -> None:
    record = envelope().to_mapping()
    record["schema_version"] = value
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_mapping(record)


def test_unknown_and_duplicate_identity_fields_rejected() -> None:
    record = envelope().to_mapping()
    record["world"] = "implicit-alias"
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_mapping(record)
    wire = envelope().to_json()
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_json('{"event_id":"conflict",' + wire[1:])


def test_direct_construction_cannot_bypass_identity_validation() -> None:
    with pytest.raises(EnvelopeError):
        replace(envelope(), world_id="")
    with pytest.raises(EnvelopeError):
        EntityReference("Lot", EntityID("lot-1"), EntityRevision(" "))
