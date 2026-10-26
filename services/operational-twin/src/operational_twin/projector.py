"""Deterministic, read-only projection core.

The projector owns a rebuildable read model. It never emits commands or mutates
canonical manufacturing state. Event identity and aggregate versions are kept
separately so retries, stale deliveries and gaps cannot silently advance state.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


class AdmissionError(ValueError):
    """The event cannot be admitted into this world's projection."""


class ProjectionOrderError(AdmissionError):
    """An event is older than the applied aggregate revision."""


class ProjectionGap(AdmissionError):
    """An event skips an aggregate revision and requires reconciliation."""


@dataclass(frozen=True)
class ProjectionEvent:
    event_id: str
    event_type: str
    world_id: str
    aggregate_type: str
    aggregate_id: str
    aggregate_version: int
    payload: Mapping[str, Any]
    branch_id: str = "PRIMARY"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProjectionEvent":
        required = {
            "event_id", "event_type", "world_id", "aggregate_type",
            "aggregate_id", "aggregate_version", "payload",
        }
        if set(value) - required - {"branch_id"} or not required <= set(value):
            raise AdmissionError("event: required projection fields missing")
        text_fields = ("event_id", "event_type", "world_id", "aggregate_type", "aggregate_id")
        if any(not isinstance(value[name], str) or not value[name].strip() for name in text_fields):
            raise AdmissionError("event: nonblank identity required")
        version = value["aggregate_version"]
        if type(version) is not int or version < 1:
            raise AdmissionError("aggregate_version: positive integer required")
        payload = value["payload"]
        if not isinstance(payload, Mapping):
            raise AdmissionError("payload: object required")
        branch = value.get("branch_id", "PRIMARY")
        if not isinstance(branch, str) or not branch.strip():
            raise AdmissionError("branch_id: nonblank string required")
        return cls(**{**value, "branch_id": branch})


@dataclass
class ProjectionState:
    world_id: str
    branch_id: str = "PRIMARY"
    entities: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    applied_events: dict[str, int] = field(default_factory=dict)
    aggregate_revisions: dict[tuple[str, str], int] = field(default_factory=dict)
    source_revision: str | None = None
    status: str = "FRESH"

    def snapshot(self) -> dict[str, Any]:
        return {
            "world_id": self.world_id,
            "branch_id": self.branch_id,
            "entities": deepcopy(self.entities),
            "applied_events": dict(self.applied_events),
            "aggregate_revisions": dict(self.aggregate_revisions),
            "source_revision": self.source_revision,
            "status": self.status,
        }


@dataclass(frozen=True)
class ApplyResult:
    outcome: str
    event_id: str
    source_revision: str
    status: str


Handler = Callable[[ProjectionState, ProjectionEvent], None]


def _entity_key(event: ProjectionEvent) -> tuple[str, str]:
    return event.aggregate_type, event.aggregate_id


def _set_entity(state: ProjectionState, event: ProjectionEvent, **fields: Any) -> None:
    key = _entity_key(event)
    current = dict(state.entities.get(key, {}))
    current.update(fields)
    current.update(
        aggregate_type=event.aggregate_type,
        aggregate_id=event.aggregate_id,
        aggregate_version=event.aggregate_version,
        source_event_id=event.event_id,
        source_revision=event.payload.get("source_revision", event.event_id),
    )
    state.entities[key] = current


def _production(state: ProjectionState, event: ProjectionEvent) -> None:
    if event.event_type == "production.lot-held":
        _set_entity(state, event, lifecycle="HELD", hold_id=event.payload.get("material_hold_id"),
                    hold_reason=event.payload.get("reason"))
    elif event.event_type == "production.lot-dispatch-authorized":
        _set_entity(state, event, dispatch_id=event.payload.get("dispatch_id"), dispatchable=True)
    else:
        _set_entity(state, event, observation="PRODUCTION_EVENT", payload=dict(event.payload))


def _equipment(state: ProjectionState, event: ProjectionEvent) -> None:
    _set_entity(state, event, equipment_state=event.payload.get("state", event.payload.get("status", "OBSERVED")),
                payload=dict(event.payload))


def _quality(state: ProjectionState, event: ProjectionEvent) -> None:
    _set_entity(state, event, quality_state=event.payload.get("state", "OBSERVED"),
                payload=dict(event.payload))


HANDLERS: dict[str, Handler] = {
    "production": _production,
    "equipment": _equipment,
    "quality": _quality,
}


class Projector:
    """Apply admitted events to one explicitly scoped operational world."""

    def __init__(self, state: ProjectionState):
        if not state.world_id.strip() or not state.branch_id.strip():
            raise AdmissionError("projection scope must be explicit")
        self.state = state

    def apply(self, event: ProjectionEvent) -> ApplyResult:
        if event.world_id != self.state.world_id or event.branch_id != self.state.branch_id:
            raise AdmissionError("event scope does not match projection")
        if event.event_id in self.state.applied_events:
            return ApplyResult("DUPLICATE", event.event_id, self.state.source_revision or event.event_id, self.state.status)
        key = _entity_key(event)
        previous = self.state.aggregate_revisions.get(key, 0)
        if event.aggregate_version <= previous:
            raise ProjectionOrderError("event is older than applied aggregate revision")
        if event.aggregate_version != previous + 1:
            self.state.status = "STALE"
            raise ProjectionGap("aggregate revision gap requires reconciliation")
        namespace = event.event_type.split(".", 1)[0]
        handler = HANDLERS.get(namespace)
        if handler is None:
            raise AdmissionError("unsupported event namespace")
        handler(self.state, event)
        self.state.applied_events[event.event_id] = event.aggregate_version
        self.state.aggregate_revisions[key] = event.aggregate_version
        self.state.source_revision = event.event_id
        self.state.status = "FRESH"
        return ApplyResult("PROCESSED", event.event_id, event.event_id, self.state.status)

    def catch_up(self, events: list[ProjectionEvent]) -> list[ApplyResult]:
        """Apply a deterministic ordered batch; gaps fail closed."""
        return [self.apply(event) for event in events]

    def query(self, aggregate_type: str, aggregate_id: str) -> dict[str, Any] | None:
        value = self.state.entities.get((aggregate_type, aggregate_id))
        return deepcopy(value) if value is not None else None

    def health(self) -> dict[str, Any]:
        return {
            "status": self.state.status,
            "world_id": self.state.world_id,
            "branch_id": self.state.branch_id,
            "source_revision": self.state.source_revision,
            "applied_event_count": len(self.state.applied_events),
        }

