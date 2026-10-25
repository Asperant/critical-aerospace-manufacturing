"""WP-EVT-002 metadata foundation; no payload, transport or authority inference.

EventID identifies an immutable fact across retries/replays. CorrelationID groups
the business chain; CausationID names its direct predecessor (None for a root).
TraceID identifies software execution and may change when the same fact replays.
Opaque Core identity/revision strings are preserved, never interpreted as counters.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, fields
from datetime import datetime, timedelta
from typing import Any, NewType, cast
from uuid import uuid4

EventID = NewType("EventID", str)
CorrelationID = NewType("CorrelationID", str)
CausationID = NewType("CausationID", str)
TraceID = NewType("TraceID", str)
EntityID = NewType("EntityID", str)
EntityRevision = NewType("EntityRevision", str)


class EnvelopeError(ValueError):
    """Invalid metadata; messages name fields, never supplied values."""


def _text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EnvelopeError(f"{field}: nonblank string required")


def _utc(value: object, field: str) -> None:
    if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
        raise EnvelopeError(f"{field}: aware UTC datetime required")


def _record(value: object, names: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != names:
        raise EnvelopeError("record: exact required fields expected")
    return cast(dict[str, Any], value)


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise EnvelopeError(f"{field}: UTC string required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise EnvelopeError(f"{field}: invalid UTC string") from None
    _utc(result, field)
    return result


def _utc_string(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def new_event_id() -> EventID:
    """Generate a UUID4 once per new fact; retain it on retry or replay."""
    return EventID(str(uuid4()))


@dataclass(frozen=True)
class EntityReference:
    """Typed reference only: no payload, global counter or freshness assertion."""

    entity_type: str
    id: EntityID
    revision: EntityRevision

    def __post_init__(self) -> None:
        for field in fields(self):
            _text(getattr(self, field.name), field.name)

    def to_mapping(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "id": self.id,
            "revision": self.revision,
        }

    @classmethod
    def from_mapping(cls, value: object) -> EntityReference:
        record = _record(value, {"entity_type", "id", "revision"})
        return cls(**record)


@dataclass(frozen=True)
class SimulationTime:
    """Explicit seconds on the named simulation run's clock, not a UTC instant.

    Supplied by the domain/simulator authority; never synthesized from wall time.
    This metadata type does not authenticate that authority.
    """

    seconds: float
    simulation_run_id: str

    def __post_init__(self) -> None:
        _text(self.simulation_run_id, "simulation_run_id")
        if type(self.seconds) not in (int, float):
            raise EnvelopeError("seconds: finite simulation number required")
        try:
            finite = math.isfinite(self.seconds)
        except OverflowError:
            finite = False
        if not finite:
            raise EnvelopeError("seconds: finite simulation number required")


@dataclass(frozen=True)
class EventEnvelope:
    """Operational envelope metadata, with explicit root causality and scope.

    occurred_at is either an aware UTC instant or a tagged simulation clock value.
    observed_at is always UTC wall time. No timestamp defaults to the local clock.
    The wire occurrence is discriminated by clock=UTC/SIMULATION. Entity references
    are explicitly supplied (possibly empty for events without an entity).
    Payload schemas and downstream transport integration belong to later slices.
    """

    event_id: EventID
    event_type: str
    schema_version: int
    producer: str
    world_id: str
    correlation_id: CorrelationID
    causation_id: CausationID | None
    trace_id: TraceID
    occurred_at: datetime | SimulationTime
    observed_at: datetime
    entity_refs: tuple[EntityReference, ...]

    def __post_init__(self) -> None:
        for name in (
            "event_id",
            "event_type",
            "producer",
            "world_id",
            "correlation_id",
            "trace_id",
        ):
            _text(getattr(self, name), name)
        if self.causation_id is not None:
            _text(self.causation_id, "causation_id")
        if type(self.schema_version) is not int or self.schema_version < 1:
            raise EnvelopeError("schema_version: positive integer required")
        _utc(self.observed_at, "observed_at")
        if not isinstance(self.occurred_at, SimulationTime):
            _utc(self.occurred_at, "occurred_at")
        if not isinstance(self.entity_refs, tuple) or any(
            not isinstance(ref, EntityReference) for ref in self.entity_refs
        ):
            raise EnvelopeError("entity_refs: tuple of EntityReference required")

    def to_mapping(self) -> dict[str, object]:
        occurrence: dict[str, object]
        if isinstance(self.occurred_at, SimulationTime):
            occurrence = {
                "clock": "SIMULATION",
                "seconds": self.occurred_at.seconds,
                "simulation_run_id": self.occurred_at.simulation_run_id,
            }
        else:
            occurrence = {"clock": "UTC", "value": _utc_string(self.occurred_at)}
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "schema_version": self.schema_version,
            "producer": self.producer,
            "world_id": self.world_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "trace_id": self.trace_id,
            "occurred_at": occurrence,
            "observed_at": _utc_string(self.observed_at),
            "entity_refs": [ref.to_mapping() for ref in self.entity_refs],
        }

    @classmethod
    def from_mapping(cls, value: object) -> EventEnvelope:
        record = _record(value, {field.name for field in fields(cls)}).copy()
        occurrence = record["occurred_at"]
        if not isinstance(occurrence, dict):
            raise EnvelopeError("occurred_at: explicit clock required")
        if occurrence.get("clock") == "UTC":
            utc = _record(occurrence, {"clock", "value"})
            record["occurred_at"] = _parse_utc(utc["value"], "occurred_at")
        elif occurrence.get("clock") == "SIMULATION":
            simulation = _record(occurrence, {"clock", "seconds", "simulation_run_id"})
            record["occurred_at"] = SimulationTime(
                seconds=simulation["seconds"],
                simulation_run_id=simulation["simulation_run_id"],
            )
        else:
            raise EnvelopeError("occurred_at: unknown clock")
        record["observed_at"] = _parse_utc(record["observed_at"], "observed_at")
        if not isinstance(record["entity_refs"], list):
            raise EnvelopeError("entity_refs: array required")
        record["entity_refs"] = tuple(
            EntityReference.from_mapping(ref) for ref in record["entity_refs"]
        )
        return cls(**record)

    def to_json(self) -> str:
        return json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> EventEnvelope:
        def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            result: dict[str, Any] = {}
            for key, item in pairs:
                if key in result:
                    raise EnvelopeError("record: duplicate field")
                result[key] = item
            return result

        def invalid_constant(_: str) -> None:
            raise EnvelopeError("record: nonfinite JSON number")

        try:
            decoded = json.loads(
                value, object_pairs_hook=unique, parse_constant=invalid_constant
            )
        except (ValueError, TypeError):
            raise EnvelopeError("record: invalid envelope JSON") from None
        return cls.from_mapping(decoded)


def validate_world_scope(
    envelope: EventEnvelope, expected_world_id: str | None
) -> EventEnvelope:
    """Require the consumer's explicit world and return the same envelope.

    Compare opaque IDs exactly, without normalization, inference or mutation.
    This checks scope equality only; it does not authenticate or authorize callers.
    """
    _text(expected_world_id, "expected_world_id")
    _text(envelope.world_id, "world_id")
    if envelope.world_id != expected_world_id:
        raise EnvelopeError("world_id: scope mismatch")
    return envelope
