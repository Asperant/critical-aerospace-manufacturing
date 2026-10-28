"""Operational state and event exposure without evaluator-only truth (FR-SIM-014).

Everything leaves through a positive allow-list: a field that is not named here
cannot be exposed, whatever the producing code holds. Exposure is local and typed.
It is not publication on the event spine, and it never reaches hidden Oracle state.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from manufacturing_simulator.decision import PROVENANCE, Candidate, DecisionRequest
from manufacturing_simulator.errors import SimulatorError
from manufacturing_simulator.isolation import is_evaluator_field
from manufacturing_simulator.ports import FacilityPort

EVENT_KINDS = frozenset(
    {
        "DISPATCH_ACCEPTED",
        "DISPATCH_REJECTED",
        "DISPATCH_STARTED",
        "DISPATCH_START_REJECTED",
        "LOT_RELEASED",
        "LOT_QUEUED",
        "PROCESS_COMPLETED",
        "LOT_COMPLETED",
        "LOT_SCRAPPED",
        "LOT_SCRAP_REJECTED",
        "INSPECTION_FAILED",
        "REWORK_REQUESTED",
        "REWORK_STARTED",
        "REWORK_REJECTED",
        "HOLD_PLACED",
        "HOLD_RELEASED",
        "EQUIPMENT_FAILED",
        "EQUIPMENT_REPAIRED",
        "EQUIPMENT_AVAILABLE",
        "EQUIPMENT_DEGRADED",
        "MAINTENANCE_STARTED",
        "MAINTENANCE_COMPLETED",
        "MAINTENANCE_SKIPPED",
    }
)
ALLOWED_ATTRIBUTES = frozenset(
    {
        "dispatch_id",
        "request_id",
        "lot_id",
        "machine_id",
        "route_step",
        "rule_id",
        "reason_code",
        "state_revision",
        "directive_id",
        "from_state",
        "to_state",
    }
)


class ExposureError(SimulatorError):
    """Something that is not allow-listed was offered for exposure."""


@dataclass(frozen=True)
class OperationalEvent:
    """One operational fact, labelled as simulation output."""

    kind: str
    time: int
    world_id: str
    correlation_id: str
    attributes: tuple[tuple[str, str], ...]
    provenance: str = PROVENANCE

    def to_document(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "time": self.time,
            "world_id": self.world_id,
            "correlation_id": self.correlation_id,
            "provenance": self.provenance,
            "attributes": dict(self.attributes),
        }


def make_event(
    kind: str,
    time: int,
    world_id: str,
    correlation_id: str,
    attributes: Mapping[str, str | None],
) -> OperationalEvent:
    """Build an event, refusing any kind or attribute outside the allow-lists."""
    if kind not in EVENT_KINDS:
        raise ExposureError("event kind is not exposed")
    kept: list[tuple[str, str]] = []
    for name, value in attributes.items():
        if is_evaluator_field(name) or name not in ALLOWED_ATTRIBUTES:
            raise ExposureError("attribute is not exposed")
        if value is not None:
            if not isinstance(value, str):
                raise ExposureError("attribute value must be text")
            kept.append((name, value))
    return OperationalEvent(
        kind=kind,
        time=time,
        world_id=world_id,
        correlation_id=correlation_id,
        attributes=tuple(sorted(kept)),
    )


class ListPublisher:
    """In-memory publisher for tests and local runs."""

    def __init__(self) -> None:
        self.events: list[OperationalEvent] = []

    def publish(self, event: OperationalEvent) -> None:
        self.events.append(event)


@dataclass(frozen=True)
class LotState:
    lot_id: str
    revision: str
    route_step: str
    held: bool
    priority: int
    due_at: int
    ready_at: int


@dataclass(frozen=True)
class MachineState:
    machine_id: str
    available: bool


@dataclass(frozen=True)
class OperationalSnapshot:
    """A read-only operational view. Carries no evaluator-only field by construction."""

    world_id: str
    state_revision: str
    simulation_time: int
    lots: tuple[LotState, ...]
    machines: tuple[MachineState, ...]
    provenance: str = PROVENANCE


def operational_snapshot(
    world_id: str, facility: FacilityPort, now: int
) -> OperationalSnapshot:
    """Project the facility through the allow-list, in a stable order."""
    lots = tuple(
        LotState(
            lot_id=lot.lot_id,
            revision=lot.revision,
            route_step=lot.route_step,
            held=lot.held,
            priority=lot.priority,
            due_at=lot.due_at,
            ready_at=lot.ready_at,
        )
        for lot in sorted(facility.lots(), key=lambda item: item.lot_id)
    )
    machines = tuple(
        MachineState(machine_id=name, available=bool(facility.machine_available(name)))
        for name in sorted(facility.machine_ids())
    )
    return OperationalSnapshot(
        world_id=world_id,
        state_revision=facility.state_revision,
        simulation_time=now,
        lots=lots,
        machines=machines,
    )


def build_request(
    world_id: str,
    request_id: str,
    facility: FacilityPort,
    now: int,
    machine_id: str,
    exclude: Collection[str] = frozenset(),
) -> DecisionRequest:
    """The request shown to a decider when ``machine_id`` can take work.

    Only lots that are not held, are ready and may use the machine are offered, and
    never one named in ``exclude`` (for example a lot whose dispatch is already pending).
    """
    if facility.machine_available(machine_id) is None:
        raise ExposureError("unknown machine")
    offered: Sequence[Candidate] = tuple(
        Candidate(
            lot_id=lot.lot_id,
            lot_revision=lot.revision,
            route_step=lot.route_step,
            priority=lot.priority,
            due_at=lot.due_at,
            ready_at=lot.ready_at,
            eligible_machine_ids=lot.eligible_machine_ids,
        )
        for lot in sorted(facility.lots(), key=lambda item: item.lot_id)
        if not lot.held
        and lot.lot_id not in exclude
        and lot.ready_at <= now
        and machine_id in lot.eligible_machine_ids
    )
    return DecisionRequest(
        world_id=world_id,
        request_id=request_id,
        state_revision=facility.state_revision,
        simulation_time=now,
        machine_id=machine_id,
        candidates=tuple(offered),
    )
