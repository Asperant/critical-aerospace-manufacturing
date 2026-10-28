"""State vocabularies and legal transitions of the operational model (FR-SIM-002..006).

Lot lifecycle and execution states use the vocabulary and edges Core publishes in
``core.lot-operational-semantics.v1`` and enforces in its transition rules. The
Simulator never invents legality: an edge that is not listed here is rejected, and
a test compares the execution edges with Core's table. Equipment availability and
health follow the docs/02 equipment failure model.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum

from manufacturing_simulator.errors import SimulatorError


class IllegalTransition(SimulatorError):
    """A state change that no legal edge allows. Carries a code and the two states."""

    def __init__(self, kind: str, current: str, target: str) -> None:
        super().__init__(f"ILLEGAL_{kind}_TRANSITION {current} -> {target}")
        self.kind = kind
        self.current = current
        self.target = target


class ExecutionState(StrEnum):
    READY = "READY"
    QUEUED = "QUEUED"
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    PROCESSING = "PROCESSING"
    STEP_COMPLETED = "STEP_COMPLETED"


class LotLifecycle(StrEnum):
    CREATED = "CREATED"
    RELEASED = "RELEASED"
    IN_PRODUCTION = "IN_PRODUCTION"
    COMPLETED = "COMPLETED"
    SCRAPPED = "SCRAPPED"
    CANCELLED = "CANCELLED"


class EquipmentState(StrEnum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    DOWN = "DOWN"
    MAINTENANCE = "MAINTENANCE"
    QUALIFICATION = "QUALIFICATION"


class Health(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"


Edges = Mapping[str, frozenset[str]]


def _edges(table: Mapping[StrEnum, tuple[StrEnum, ...]]) -> Edges:
    return {
        src.value: frozenset(t.value for t in targets) for src, targets in table.items()
    }


EXECUTION_EDGES: Edges = _edges(
    {
        ExecutionState.READY: (ExecutionState.QUEUED,),
        ExecutionState.QUEUED: (ExecutionState.RESERVED, ExecutionState.DISPATCHED),
        ExecutionState.RESERVED: (ExecutionState.DISPATCHED,),
        ExecutionState.DISPATCHED: (ExecutionState.PROCESSING,),
        ExecutionState.PROCESSING: (ExecutionState.STEP_COMPLETED,),
        ExecutionState.STEP_COMPLETED: (ExecutionState.READY,),
    }
)

LOT_EDGES: Edges = _edges(
    {
        LotLifecycle.CREATED: (LotLifecycle.RELEASED, LotLifecycle.CANCELLED),
        LotLifecycle.RELEASED: (
            LotLifecycle.IN_PRODUCTION,
            LotLifecycle.CANCELLED,
            LotLifecycle.SCRAPPED,
        ),
        LotLifecycle.IN_PRODUCTION: (
            LotLifecycle.COMPLETED,
            LotLifecycle.CANCELLED,
            LotLifecycle.SCRAPPED,
        ),
    }
)

# docs/02: failure -> DOWN; repair -> MAINTENANCE -> (QUALIFICATION) -> AVAILABLE.
EQUIPMENT_EDGES: Edges = _edges(
    {
        EquipmentState.AVAILABLE: (
            EquipmentState.BUSY,
            EquipmentState.DOWN,
            EquipmentState.MAINTENANCE,
        ),
        EquipmentState.BUSY: (EquipmentState.AVAILABLE, EquipmentState.DOWN),
        EquipmentState.DOWN: (EquipmentState.MAINTENANCE,),
        EquipmentState.MAINTENANCE: (
            EquipmentState.AVAILABLE,
            EquipmentState.QUALIFICATION,
        ),
        EquipmentState.QUALIFICATION: (EquipmentState.AVAILABLE, EquipmentState.DOWN),
    }
)


def check(edges: Edges, kind: str, current: StrEnum, target: StrEnum) -> None:
    """Raise :class:`IllegalTransition` unless ``current -> target`` is a listed edge."""
    if target.value not in edges.get(current.value, frozenset()):
        raise IllegalTransition(kind, current.value, target.value)
