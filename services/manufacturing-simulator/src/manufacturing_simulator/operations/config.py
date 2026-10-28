"""Facility configuration: equipment, routes, lots and scenario disruptions.

Everything the operational model needs is declared here, validated before a world is
built, and reduced to a canonical document whose digest is part of the replay input.
Times are integer simulation ticks; probabilities are integer per-mille so that no
float enters the configuration.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from manufacturing_simulator.errors import InvalidConfigurationError

MAX_TICKS = 2**53 - 1


def _ident(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise InvalidConfigurationError(
            f"{name} must be a nonblank string without spaces"
        )
    return value


def _tick(value: object, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= MAX_TICKS:
        raise InvalidConfigurationError(f"{name} must be an int >= {minimum}")
    return value


def _unique(values: Sequence[str], name: str) -> None:
    if len(set(values)) != len(values):
        raise InvalidConfigurationError(f"{name} must be unique")


@dataclass(frozen=True)
class VisitSpec:
    """One re-entrant route visit; every visit has its own identity."""

    visit_id: str
    operation_class: str
    eligible_equipment: tuple[str, ...]
    mean_duration: int
    inspect: bool = False
    defect_per_mille: int = 0

    def __post_init__(self) -> None:
        _ident(self.visit_id, "visit_id")
        _ident(self.operation_class, "operation_class")
        if not self.eligible_equipment:
            raise InvalidConfigurationError(
                "a visit needs at least one eligible equipment"
            )
        for name in self.eligible_equipment:
            _ident(name, "eligible equipment")
        _unique(self.eligible_equipment, "eligible equipment")
        _tick(self.mean_duration, "mean_duration", minimum=1)
        if (
            type(self.defect_per_mille) is not int
            or not 0 <= self.defect_per_mille <= 1000
        ):
            raise InvalidConfigurationError(
                "defect_per_mille must be an int in 0..1000"
            )


@dataclass(frozen=True)
class RouteSpec:
    route_id: str
    revision: str
    visits: tuple[VisitSpec, ...]

    def __post_init__(self) -> None:
        _ident(self.route_id, "route_id")
        _ident(self.revision, "route revision")
        if not self.visits:
            raise InvalidConfigurationError("a route needs at least one visit")
        _unique([v.visit_id for v in self.visits], "visit ids of a route")


@dataclass(frozen=True)
class EquipmentSpec:
    """A machine: what it can do, how it fails and degrades, how it is repaired."""

    equipment_id: str
    operation_classes: tuple[str, ...]
    mtbf: int | None = None
    mttr: int = 10
    qualification: int = 0
    degrade_after: int | None = None
    critical_after: int | None = None

    def __post_init__(self) -> None:
        _ident(self.equipment_id, "equipment_id")
        if not self.operation_classes:
            raise InvalidConfigurationError("equipment needs an operation class")
        for name in self.operation_classes:
            _ident(name, "operation class")
        if self.mtbf is not None:
            _tick(self.mtbf, "mtbf", minimum=1)
        _tick(self.mttr, "mttr", minimum=1)
        _tick(self.qualification, "qualification")
        for label, value in (
            ("degrade_after", self.degrade_after),
            ("critical_after", self.critical_after),
        ):
            if value is not None:
                _tick(value, label, minimum=1)
        if (
            self.degrade_after is not None
            and self.critical_after is not None
            and self.critical_after <= self.degrade_after
        ):
            raise InvalidConfigurationError("critical_after must exceed degrade_after")


@dataclass(frozen=True)
class LotSpec:
    lot_id: str
    order_id: str
    route_id: str
    release_at: int = 0
    priority: int = 1
    due_at: int = MAX_TICKS

    def __post_init__(self) -> None:
        _ident(self.lot_id, "lot_id")
        _ident(self.order_id, "order_id")
        _ident(self.route_id, "route_id")
        _tick(self.release_at, "release_at")
        _tick(self.priority, "priority")
        _tick(self.due_at, "due_at")


@dataclass(frozen=True)
class FailureSpec:
    """A scheduled (deterministic) equipment failure."""

    equipment_id: str
    at: int

    def __post_init__(self) -> None:
        _ident(self.equipment_id, "equipment_id")
        _tick(self.at, "failure time")


@dataclass(frozen=True)
class MaintenanceSpec:
    """A planned maintenance window; it starts when the equipment is idle."""

    equipment_id: str
    start_at: int
    duration: int

    def __post_init__(self) -> None:
        _ident(self.equipment_id, "equipment_id")
        _tick(self.start_at, "start_at")
        _tick(self.duration, "duration", minimum=1)


@dataclass(frozen=True)
class HoldSpec:
    """A material hold imposed from outside (Core owns holds); released_at may be None."""

    lot_id: str
    placed_at: int
    released_at: int | None = None

    def __post_init__(self) -> None:
        _ident(self.lot_id, "lot_id")
        _tick(self.placed_at, "placed_at")
        if (
            self.released_at is not None
            and _tick(self.released_at, "released_at") <= self.placed_at
        ):
            raise InvalidConfigurationError("a hold is released after it is placed")


@dataclass(frozen=True)
class ReworkDirectiveSpec:
    """A rework directive injected the way Core would issue it (never created here)."""

    directive_id: str
    lot_id: str
    at: int
    origin_visit_id: str
    return_visit_id: str
    rework_route_id: str
    approval: str = "APPROVED"

    def __post_init__(self) -> None:
        for name in (
            "directive_id",
            "lot_id",
            "origin_visit_id",
            "return_visit_id",
            "rework_route_id",
        ):
            _ident(getattr(self, name), name)
        _tick(self.at, "directive time")
        if self.approval not in {"APPROVED", "PENDING", "REJECTED"}:
            raise InvalidConfigurationError(
                "approval must be APPROVED, PENDING or REJECTED"
            )


@dataclass(frozen=True)
class ScrapSpec:
    lot_id: str
    at: int

    def __post_init__(self) -> None:
        _ident(self.lot_id, "lot_id")
        _tick(self.at, "scrap time")


@dataclass(frozen=True)
class FacilityConfig:
    """The complete, validated description of one simulated facility."""

    world_id: str
    equipment: tuple[EquipmentSpec, ...]
    routes: tuple[RouteSpec, ...]
    lots: tuple[LotSpec, ...]
    failures: tuple[FailureSpec, ...] = ()
    maintenance: tuple[MaintenanceSpec, ...] = ()
    holds: tuple[HoldSpec, ...] = ()
    reworks: tuple[ReworkDirectiveSpec, ...] = ()
    scraps: tuple[ScrapSpec, ...] = ()
    rework_routes: tuple[RouteSpec, ...] = field(default=())
    max_rework: int = 2

    def __post_init__(self) -> None:
        _ident(self.world_id, "world_id")
        _tick(self.max_rework, "max_rework")
        equipment = {e.equipment_id: e for e in self.equipment}
        _unique([e.equipment_id for e in self.equipment], "equipment ids")
        route_ids = [r.route_id for r in (*self.routes, *self.rework_routes)]
        _unique(route_ids, "route ids")
        for route in (*self.routes, *self.rework_routes):
            for visit in route.visits:
                for name in visit.eligible_equipment:
                    spec = equipment.get(name)
                    if spec is None:
                        raise InvalidConfigurationError(
                            f"unknown equipment {name!r} in {visit.visit_id}"
                        )
                    if visit.operation_class not in spec.operation_classes:
                        raise InvalidConfigurationError(
                            f"{name} cannot do {visit.operation_class}"
                        )
        _unique([lot.lot_id for lot in self.lots], "lot ids")
        main = {r.route_id for r in self.routes}
        for lot in self.lots:
            if lot.route_id not in main:
                raise InvalidConfigurationError(
                    f"lot {lot.lot_id} names an unknown route"
                )
        lots = {lot.lot_id for lot in self.lots}
        for item in (*self.holds, *self.reworks, *self.scraps):
            if item.lot_id not in lots:
                raise InvalidConfigurationError("a disruption names an unknown lot")
        for item in (*self.failures, *self.maintenance):
            if item.equipment_id not in equipment:
                raise InvalidConfigurationError("a disruption names unknown equipment")
        _unique([r.directive_id for r in self.reworks], "directive ids")
        rework_routes = {r.route_id for r in self.rework_routes}
        for directive in self.reworks:
            if directive.rework_route_id not in rework_routes:
                raise InvalidConfigurationError(
                    "a directive names an unknown rework route"
                )

    def to_document(self) -> dict[str, Any]:
        """Canonical, JSON-ready description; the basis of :meth:`digest`."""

        def plain(value: Any) -> Any:
            if hasattr(value, "__dataclass_fields__"):
                return {n: plain(getattr(value, n)) for n in value.__dataclass_fields__}
            if isinstance(value, tuple | list):
                return [plain(v) for v in value]
            return value

        document: dict[str, Any] = plain(self)
        return document

    def digest(self) -> str:
        text = json.dumps(self.to_document(), sort_keys=True, separators=(",", ":"))
        return "sha256:" + hashlib.sha256(text.encode("ascii")).hexdigest()
