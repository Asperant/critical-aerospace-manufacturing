"""TEST-EVT-002-001: TEST-EVT-ENVELOPE / TEST-DATA-TIME, isolated unit fixtures.

Metadata foundation only; no service trace propagation or REAL acceptance claim.
"""

import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, cast
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
from jsonschema import Draft202012Validator

WALL_TIME = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
CONTRACTS = Path(__file__).resolve().parents[2] / "packages/contracts"
ENVELOPE_SCHEMA: dict[str, Any] = json.loads(
    (CONTRACTS / "schemas/event-envelope.v1.schema.json").read_text()
)


class MetadataValidator(Protocol):
    """Typed surface for jsonschema's partially typed validation methods."""

    def validate(self, instance: object) -> None: ...

    def is_valid(self, instance: object) -> bool: ...


ENVELOPE_VALIDATOR = cast(MetadataValidator, Draft202012Validator(ENVELOPE_SCHEMA))


def assert_invalid_metadata(record: object) -> None:
    """Both independent validators reject the same malformed wire metadata."""
    assert not ENVELOPE_VALIDATOR.is_valid(record)
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_mapping(record)


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
    ENVELOPE_VALIDATOR.validate(original.to_mapping())


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
    assert_invalid_metadata(record)


@pytest.mark.parametrize(
    "field",
    ["event_id", "correlation_id", "causation_id", "trace_id", "world_id", "producer"],
)
@pytest.mark.parametrize("value", ["", " \t\n", 1, True, [], {}])
def test_malformed_identity_fields_rejected(field: str, value: object) -> None:
    record = envelope().to_mapping()
    record[field] = value
    assert_invalid_metadata(record)


@pytest.mark.parametrize(
    "field", ["event_id", "correlation_id", "trace_id", "world_id", "producer"]
)
def test_null_identity_rejected(field: str) -> None:
    record = envelope().to_mapping()
    record[field] = None
    assert_invalid_metadata(record)


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
    wire = envelope().to_mapping()
    wire["entity_refs"] = [record]
    assert_invalid_metadata(wire)


@pytest.mark.parametrize("field", ["entity_type", "id", "revision"])
def test_missing_entity_reference_field_rejected(field: str) -> None:
    record = {"entity_type": "Lot", "id": "lot-1", "revision": "rev-A"}
    del record[field]
    with pytest.raises(EnvelopeError):
        EntityReference.from_mapping(record)
    wire = envelope().to_mapping()
    wire["entity_refs"] = [record]
    assert_invalid_metadata(wire)


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
            ENVELOPE_VALIDATOR.validate(restored.to_mapping())
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
    assert_invalid_metadata(record)


@pytest.mark.parametrize("value", [True, 0, -1, "1", None])
def test_malformed_schema_version_rejected(value: object) -> None:
    record = envelope().to_mapping()
    record["schema_version"] = value
    assert_invalid_metadata(record)


def test_unknown_and_duplicate_identity_fields_rejected() -> None:
    record = envelope().to_mapping()
    record["world"] = "implicit-alias"
    assert_invalid_metadata(record)
    wire = envelope().to_json()
    with pytest.raises(EnvelopeError):
        EventEnvelope.from_json('{"event_id":"conflict",' + wire[1:])


def test_direct_construction_cannot_bypass_identity_validation() -> None:
    with pytest.raises(EnvelopeError):
        replace(envelope(), world_id="")
    with pytest.raises(EnvelopeError):
        EntityReference("Lot", EntityID("lot-1"), EntityRevision(" "))


def test_envelope_schema_is_valid_and_fields_match_model() -> None:
    Draft202012Validator.check_schema(ENVELOPE_SCHEMA)
    model_keys = set(envelope().to_mapping())
    assert set(ENVELOPE_SCHEMA["required"]) == model_keys
    assert set(ENVELOPE_SCHEMA["properties"]) == model_keys


@pytest.mark.parametrize("clock", ["utc", "simulation"])
def test_published_fixtures_schema_model_round_trip(clock: str) -> None:
    fixture: dict[str, Any] = json.loads(
        (CONTRACTS / f"fixtures/event-envelope.{clock}.json").read_text()
    )
    ENVELOPE_VALIDATOR.validate(fixture)
    model = EventEnvelope.from_mapping(fixture)
    assert model.to_mapping() == fixture
    assert EventEnvelope.from_json(model.to_json()) == model
    ENVELOPE_VALIDATOR.validate(model.to_mapping())
    assert (
        model.event_id,
        model.correlation_id,
        model.causation_id,
        model.trace_id,
    ) == (
        fixture["event_id"],
        fixture["correlation_id"],
        fixture["causation_id"],
        fixture["trace_id"],
    )
    assert model.entity_refs[0].revision == "lot-rA"
    assert model.world_id == "SYNTHETIC-WORLD"
    assert model.observed_at == datetime(2026, 10, 25, 12, 0, 2, 123456, tzinfo=UTC)
    if clock == "utc":
        assert model.occurred_at == datetime(2026, 10, 25, 12, 0, 0, 123456, tzinfo=UTC)
        assert model.causation_id is None
    else:
        assert model.occurred_at == SimulationTime(42.5, "SYNTHETIC-RUN-1")
        assert model.causation_id == "00000000-0000-4000-8000-000000000001"


@pytest.mark.parametrize("clock", ["utc", "simulation"])
@pytest.mark.parametrize(
    "field", ["world_id", "event_id", "correlation_id", "causation_id", "trace_id"]
)
def test_published_fixtures_missing_identity_rejected(clock: str, field: str) -> None:
    fixture: dict[str, Any] = json.loads(
        (CONTRACTS / f"fixtures/event-envelope.{clock}.json").read_text()
    )
    del fixture[field]
    assert_invalid_metadata(fixture)


@pytest.mark.parametrize("clock", ["utc", "simulation"])
@pytest.mark.parametrize("field", ["id", "revision"])
@pytest.mark.parametrize("value", [None, "", " \t", 3])
def test_published_fixtures_malformed_reference_rejected(
    clock: str, field: str, value: object
) -> None:
    fixture: dict[str, Any] = json.loads(
        (CONTRACTS / f"fixtures/event-envelope.{clock}.json").read_text()
    )
    fixture["entity_refs"][0][field] = value
    assert_invalid_metadata(fixture)


@pytest.mark.parametrize(
    "value",
    [
        "0000-01-01T00:00:00Z",
        "1900-02-29T00:00:00Z",
        "2026-02-29T00:00:00Z",
        "2026-04-31T00:00:00Z",
        "2026-10-25T24:00:00Z",
        "2026-10-25T12:00:60Z",
        "2026-10-25T12:00:00",
        "2026-10-25T12:00:00+03:00",
        "invalid-date",
    ],
)
def test_utc_schema_and_model_reject_invalid_calendar_and_clock(value: str) -> None:
    fixture = envelope().to_mapping()
    fixture["observed_at"] = value
    assert_invalid_metadata(fixture)
    fixture = envelope().to_mapping()
    fixture["occurred_at"] = {"clock": "UTC", "value": value}
    assert_invalid_metadata(fixture)


@pytest.mark.parametrize(
    "value",
    [
        "0001-01-01T00:00:00Z",
        "2000-02-29T23:59:59Z",
        "2024-02-29T00:00:00Z",
        "2400-02-29T00:00:00Z",
        "9999-12-31T23:59:59.999999Z",
        "2026-10-25T12:00:00.1+00:00",
    ],
)
def test_utc_schema_and_model_accept_boundary_dates(value: str) -> None:
    fixture = envelope().to_mapping()
    fixture["observed_at"] = value
    fixture["occurred_at"] = {"clock": "UTC", "value": value}
    ENVELOPE_VALIDATOR.validate(fixture)
    ENVELOPE_VALIDATOR.validate(EventEnvelope.from_mapping(fixture).to_mapping())


@pytest.mark.parametrize(
    "value", [None, "", {}, [None], [{"id": "x", "revision": "r1"}]]
)
def test_reference_structure_parity(value: object) -> None:
    fixture = envelope().to_mapping()
    fixture["entity_refs"] = value
    assert_invalid_metadata(fixture)


def test_scope_clock_and_reference_records_are_closed() -> None:
    for field, value in (
        (
            "occurred_at",
            {"clock": "UTC", "value": "2026-10-25T12:00:00Z", "seconds": 42},
        ),
        (
            "occurred_at",
            {
                "clock": "SIMULATION",
                "seconds": 42,
                "simulation_run_id": "run-1",
                "value": "2026-10-25T12:00:00Z",
            },
        ),
        (
            "entity_refs",
            [{"entity_type": "Lot", "id": "L1", "revision": "r1", "counter": 1}],
        ),
        ("payload", {}),
    ):
        fixture = envelope().to_mapping()
        fixture[field] = value
        assert_invalid_metadata(fixture)


@pytest.mark.parametrize("seconds", [-1.5, 0, 42.5])
def test_simulation_numbers_remain_seconds_without_utc_conversion(
    seconds: float,
) -> None:
    model = replace(envelope(), occurred_at=SimulationTime(seconds, "run-1"))
    ENVELOPE_VALIDATOR.validate(model.to_mapping())
    restored = EventEnvelope.from_mapping(model.to_mapping())
    assert restored.occurred_at == SimulationTime(seconds, "run-1")
    assert restored.observed_at == WALL_TIME
