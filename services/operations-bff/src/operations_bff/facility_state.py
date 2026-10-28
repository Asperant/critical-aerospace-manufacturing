"""Read-only Twin-backed facility state query for the Command Center.

The BFF forwards an explicit world and session-derived actor to this port. It
does not own lifecycle, execution, hold, equipment, or route state and never
turns a missing Twin response into an empty facility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .actor import ActorContext
from .errors import Unavailable
from .overview import FRESHNESS_ORDER, SourceUnavailable
from .session import format_timestamp

TWIN_SOURCE = "digital-twin-service"
EPISTEMIC_CLASSES = frozenset(
    {
        "ACTUAL",
        "OBSERVED",
        "INFERRED",
        "PREDICTED",
        "PLANNED",
        "COUNTERFACTUAL",
        "STALE",
    }
)
FRESHNESS = frozenset(FRESHNESS_ORDER)


@dataclass(frozen=True)
class FacilityStateQuery:
    world_id: str
    simulation_run_id: str | None
    branch_id: str | None
    as_of: datetime | None
    actor: ActorContext
    correlation_id: str


@dataclass(frozen=True)
class EquipmentState:
    equipment_id: str
    revision: str
    equipment_state: str
    maintenance_state: str
    epistemic_class: str
    freshness: str


@dataclass(frozen=True)
class RoutePosition:
    route_id: str
    visit_id: str
    position: int
    operation_class_id: str


@dataclass(frozen=True)
class LotState:
    lot_id: str
    revision: str
    lifecycle_state: str
    execution_state: str
    hold_state: str
    route_position: RoutePosition
    epistemic_class: str
    freshness: str


@dataclass(frozen=True)
class FacilityStateSnapshot:
    source: str
    revision: str
    as_of: datetime
    freshness: str
    equipment: tuple[EquipmentState, ...]
    lots: tuple[LotState, ...]


class FacilityStateReader(Protocol):
    @property
    def name(self) -> str: ...

    def read(self, query: FacilityStateQuery) -> FacilityStateSnapshot:
        """Read one explicitly scoped Twin snapshot."""
        ...


def _text(value: str, field: str) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid(snapshot: FacilityStateSnapshot, name: str) -> bool:
    if (
        snapshot.source != name
        or not _text(snapshot.revision, "revision")
        or snapshot.as_of.tzinfo is None
        or snapshot.freshness not in FRESHNESS
        or len({item.equipment_id for item in snapshot.equipment})
        != len(snapshot.equipment)
        or len({item.lot_id for item in snapshot.lots}) != len(snapshot.lots)
    ):
        return False
    for item in snapshot.equipment:
        if not all(
            (
                _text(item.equipment_id, "equipment_id"),
                _text(item.revision, "revision"),
                _text(item.equipment_state, "equipment_state"),
                _text(item.maintenance_state, "maintenance_state"),
                item.epistemic_class in EPISTEMIC_CLASSES,
                item.freshness in FRESHNESS,
            )
        ):
            return False
    for item in snapshot.lots:
        route = item.route_position
        if not all(
            (
                _text(item.lot_id, "lot_id"),
                _text(item.revision, "revision"),
                _text(item.lifecycle_state, "lifecycle_state"),
                _text(item.execution_state, "execution_state"),
                _text(item.hold_state, "hold_state"),
                item.epistemic_class in EPISTEMIC_CLASSES,
                item.freshness in FRESHNESS,
                _text(route.route_id, "route_id"),
                _text(route.visit_id, "visit_id"),
                type(route.position) is int and route.position >= 0,
                _text(route.operation_class_id, "operation_class_id"),
            )
        ):
            return False
    return True


class FacilityStateService:
    def __init__(self, reader: FacilityStateReader) -> None:
        if reader.name != TWIN_SOURCE:
            raise ValueError(f"facility state reader must be {TWIN_SOURCE}")
        self._reader = reader

    def get(
        self,
        query: FacilityStateQuery,
        *,
        now: datetime,
        correlation_id: str,
    ) -> dict[str, object]:
        try:
            snapshot = self._reader.read(query)
        except SourceUnavailable:
            raise Unavailable(
                "The Twin facility state is unavailable",
                details={"unavailable_sources": [TWIN_SOURCE], "required": True},
            ) from None
        if not _valid(snapshot, self._reader.name):
            raise Unavailable(
                "The Twin facility state is invalid or unavailable",
                details={"unavailable_sources": [TWIN_SOURCE], "required": True},
            )
        return {
            "contract_version": "bff.facility-state.v1",
            "meta": {
                "revision": _view_revision(query, snapshot),
                "as_of": format_timestamp(snapshot.as_of),
                "generated_at": format_timestamp(now),
                "freshness": snapshot.freshness,
                "world": _world(query),
                "sources": [
                    {
                        "source": snapshot.source,
                        "revision": snapshot.revision,
                        "as_of": format_timestamp(snapshot.as_of),
                        "freshness": snapshot.freshness,
                    }
                ],
                "correlation_id": correlation_id,
            },
            "facility": {
                "equipment": [
                    {
                        "equipment_id": item.equipment_id,
                        "revision": item.revision,
                        "equipment_state": item.equipment_state,
                        "maintenance_state": item.maintenance_state,
                        "epistemic_class": item.epistemic_class,
                        "freshness": item.freshness,
                    }
                    for item in snapshot.equipment
                ],
                "lots": [
                    {
                        "lot_id": item.lot_id,
                        "revision": item.revision,
                        "lifecycle_state": item.lifecycle_state,
                        "execution_state": item.execution_state,
                        "hold_state": item.hold_state,
                        "route_position": {
                            "route_id": item.route_position.route_id,
                            "visit_id": item.route_position.visit_id,
                            "position": item.route_position.position,
                            "operation_class_id": item.route_position.operation_class_id,
                        },
                        "epistemic_class": item.epistemic_class,
                        "freshness": item.freshness,
                    }
                    for item in snapshot.lots
                ],
            },
        }


def _world(query: FacilityStateQuery) -> dict[str, str]:
    world = {"world_id": query.world_id}
    if query.simulation_run_id:
        world["simulation_run_id"] = query.simulation_run_id
    if query.branch_id:
        world["branch_id"] = query.branch_id
    return world


def _view_revision(query: FacilityStateQuery, snapshot: FacilityStateSnapshot) -> str:
    canonical = json.dumps(
        {
            "world": _world(query),
            "source": snapshot.source,
            "revision": snapshot.revision,
            "equipment": [item.__dict__ for item in snapshot.equipment],
            "lots": [
                {**item.__dict__, "route_position": item.route_position.__dict__}
                for item in snapshot.lots
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return "state-" + hashlib.sha256(canonical.encode()).hexdigest()[:16]
