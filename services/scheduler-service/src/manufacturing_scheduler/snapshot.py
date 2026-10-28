"""Strict, immutable consumer of the published ``core.scheduling-snapshot.v1``.

Consumed fields (exactly the published v1 shape, nothing assumed beyond it):
``contract_version``, ``world_id``, ``snapshot_revision``, ``generated_at``,
``freshness.status``, ``freshness.valid_until``, per lot ``id``, ``revision``,
``route_position.{route_id,visit_id,position,operation_class_id}``, ``priority``,
``due_at`` and ``eligible_equipment_ids``, per equipment ``id``, ``revision`` and
``maintenance_state``, and ``current_schedule_version``.

The snapshot carries no processing times, remaining route, holds, queues,
maintenance windows or simulation time. :class:`PlanningInput` therefore names those
gaps instead of inventing values, and refuses to become a full optimizer instance.
Every identity and revision is kept as the exact opaque string the producer sent.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from manufacturing_scheduler.errors import IncompleteInputError, SnapshotError
from manufacturing_scheduler.wire import Reader, loads_strict, reject_oracle_fields

SNAPSHOT_CONTRACT = "core.scheduling-snapshot.v1"
_TOP = (
    "contract_version",
    "world_id",
    "snapshot_revision",
    "generated_at",
    "freshness",
    "lots",
    "equipment",
    "current_schedule_version",
)
_LOT = ("id", "revision", "route_position", "priority", "due_at")
_LOT_FIELDS = (*_LOT, "eligible_equipment_ids")
_VISIT = ("route_id", "visit_id", "position", "operation_class_id")
_EQUIPMENT = ("id", "revision", "maintenance_state")


class FreshnessStatus(StrEnum):
    FRESH = "FRESH"
    DEGRADED = "DEGRADED"
    STALE = "STALE"


class MaintenanceState(StrEnum):
    """Producer maintenance label; ``AVAILABLE`` does not mean feasible to schedule."""

    AVAILABLE = "AVAILABLE"
    PLANNED_MAINTENANCE = "PLANNED_MAINTENANCE"
    IN_MAINTENANCE = "IN_MAINTENANCE"
    UNAVAILABLE = "UNAVAILABLE"


_STATUSES = tuple(member.value for member in FreshnessStatus)
_STATES = tuple(member.value for member in MaintenanceState)


class Usability(StrEnum):
    NORMAL = "NORMAL"
    DIAGNOSTIC_ONLY = "DIAGNOSTIC_ONLY"


class InputGap(StrEnum):
    """Optimizer inputs the v1 snapshot does not carry."""

    PROCESSING_DURATIONS = "PROCESSING_DURATIONS"
    REMAINING_ROUTE = "REMAINING_ROUTE"
    MATERIAL_HOLDS = "MATERIAL_HOLDS"
    QUEUES = "QUEUES"
    MAINTENANCE_WINDOWS = "MAINTENANCE_WINDOWS"
    SIMULATION_TIME = "SIMULATION_TIME"


class FreshnessMode(StrEnum):
    #: Only a FRESH, unexpired snapshot may be consumed.
    NORMAL = "NORMAL"
    #: A degraded, stale or expired snapshot is returned as ``DIAGNOSTIC_ONLY``.
    DIAGNOSTIC = "DIAGNOSTIC"


@dataclass(frozen=True, slots=True)
class FreshnessPolicy:
    """The caller's clock reading and mode; the package never reads a clock itself.

    A snapshot is expired when ``now >= freshness.valid_until`` (the end is
    exclusive) and from the future when ``generated_at > now`` (equality is allowed).
    There is no tolerance and no maximum age: only the producer's ``valid_until``.
    """

    now: datetime
    mode: FreshnessMode = FreshnessMode.NORMAL

    def __post_init__(self) -> None:
        if (
            not isinstance(self.now, datetime)
            or self.now.tzinfo is None
            or self.now.utcoffset() != UTC.utcoffset(None)
        ):
            raise SnapshotError("NOW_NOT_AWARE_UTC", "policy.now")
        if not isinstance(self.mode, FreshnessMode):
            raise SnapshotError("MODE_INVALID", "policy.mode")


@dataclass(frozen=True, slots=True)
class RouteVisit:
    """One visit of a (possibly re-entrant) route; never reduced to a unique step."""

    route_id: str
    visit_id: str
    position: int
    operation_class_id: str


@dataclass(frozen=True, slots=True)
class PlanningLot:
    lot_id: str
    revision: str
    visit: RouteVisit
    priority: int
    due_at: datetime
    eligible_equipment_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanningEquipment:
    equipment_id: str
    revision: str
    maintenance_state: MaintenanceState


@dataclass(frozen=True, slots=True)
class PlanningSnapshot:
    world_id: str
    snapshot_revision: str
    generated_at: datetime
    valid_until: datetime
    freshness_status: FreshnessStatus
    lots: tuple[PlanningLot, ...]
    equipment: tuple[PlanningEquipment, ...]
    current_schedule_version: str | None
    usability: Usability
    #: Why the snapshot is ``DIAGNOSTIC_ONLY`` (empty when ``NORMAL``).
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanningInput:
    """The snapshot facts plus an explicit statement of what they cannot support."""

    snapshot: PlanningSnapshot
    gaps: tuple[InputGap, ...] = tuple(InputGap)

    @property
    def complete(self) -> bool:
        return not self.gaps

    def require_full_instance(self) -> None:
        """Refuse a full optimizer instance rather than synthesize missing inputs."""

        if self.gaps:
            raise IncompleteInputError(tuple(gap.value for gap in self.gaps))


def parse_snapshot(
    payload: Mapping[str, Any], *, expected_world_id: str, policy: FreshnessPolicy
) -> PlanningSnapshot:
    """Validate a decoded snapshot against the published v1 contract and ``policy``."""

    r = Reader(SnapshotError)
    expected = r.ident(expected_world_id, "expected_world_id")
    reject_oracle_fields(payload, SnapshotError)
    top = r.obj(payload, "", _TOP)
    r.const(top["contract_version"], "/contract_version", SNAPSHOT_CONTRACT)
    if r.ident(top["world_id"], "/world_id") != expected:
        r.fail("WORLD_MISMATCH", "/world_id")
    revision = r.ident(top["snapshot_revision"], "/snapshot_revision")
    generated_at = r.timestamp(top["generated_at"], "/generated_at")
    freshness = r.obj(top["freshness"], "/freshness", ("status", "valid_until"))
    status = FreshnessStatus(
        r.enum(freshness["status"], "/freshness/status", _STATUSES)
    )
    valid_until = r.timestamp(freshness["valid_until"], "/freshness/valid_until")
    version = top["current_schedule_version"]
    if version is not None:
        version = r.ident(version, "/current_schedule_version")

    equipment: list[PlanningEquipment] = []
    equipment_ids: set[str] = set()
    for index, raw in enumerate(r.array(top["equipment"], "/equipment")):
        path = f"/equipment/{index}"
        item = r.obj(raw, path, _EQUIPMENT)
        equipment_id = r.ident(item["id"], f"{path}/id")
        if equipment_id in equipment_ids:
            r.fail("DUPLICATE_ID", f"{path}/id")
        equipment_ids.add(equipment_id)
        equipment.append(
            PlanningEquipment(
                equipment_id,
                r.ident(item["revision"], f"{path}/revision"),
                MaintenanceState(
                    r.enum(
                        item["maintenance_state"], f"{path}/maintenance_state", _STATES
                    )
                ),
            )
        )

    lots: list[PlanningLot] = []
    lot_ids: set[str] = set()
    for index, raw in enumerate(r.array(top["lots"], "/lots")):
        path = f"/lots/{index}"
        item = r.obj(raw, path, _LOT_FIELDS)
        lot_id = r.ident(item["id"], f"{path}/id")
        if lot_id in lot_ids:
            r.fail("DUPLICATE_ID", f"{path}/id")
        lot_ids.add(lot_id)
        visit = r.obj(item["route_position"], f"{path}/route_position", _VISIT)
        eligible: list[str] = []
        for slot, target in enumerate(
            r.array(item["eligible_equipment_ids"], f"{path}/eligible_equipment_ids")
        ):
            where = f"{path}/eligible_equipment_ids/{slot}"
            equipment_ref = r.ident(target, where)
            if equipment_ref in eligible:
                r.fail("DUPLICATE_ID", where)
            if equipment_ref not in equipment_ids:
                r.fail("UNKNOWN_REFERENCE", where)
            eligible.append(equipment_ref)
        lots.append(
            PlanningLot(
                lot_id,
                r.ident(item["revision"], f"{path}/revision"),
                RouteVisit(
                    r.ident(visit["route_id"], f"{path}/route_position/route_id"),
                    r.ident(visit["visit_id"], f"{path}/route_position/visit_id"),
                    r.integer(visit["position"], f"{path}/route_position/position"),
                    r.ident(
                        visit["operation_class_id"],
                        f"{path}/route_position/operation_class_id",
                    ),
                ),
                r.integer(item["priority"], f"{path}/priority"),
                r.timestamp(item["due_at"], f"{path}/due_at"),
                tuple(eligible),
            )
        )

    if valid_until <= generated_at:
        r.fail("WINDOW_INCONSISTENT", "/freshness/valid_until")
    if generated_at > policy.now:
        r.fail("SNAPSHOT_FROM_FUTURE", "/generated_at")
    reasons: list[str] = []
    if status is not FreshnessStatus.FRESH:
        reasons.append(f"STATUS_{status.value}")
    if policy.now >= valid_until:
        reasons.append("EXPIRED")
    if reasons and policy.mode is FreshnessMode.NORMAL:
        r.fail("SNAPSHOT_NOT_USABLE", "/freshness")
    return PlanningSnapshot(
        world_id=expected,
        snapshot_revision=revision,
        generated_at=generated_at,
        valid_until=valid_until,
        freshness_status=status,
        lots=tuple(lots),
        equipment=tuple(equipment),
        current_schedule_version=version,
        usability=Usability.DIAGNOSTIC_ONLY if reasons else Usability.NORMAL,
        diagnostics=tuple(reasons),
    )


def parse_snapshot_json(
    text: str, *, expected_world_id: str, policy: FreshnessPolicy
) -> PlanningSnapshot:
    """Decode JSON text strictly (duplicate fields, NaN, Infinity rejected) then parse."""

    return parse_snapshot(
        loads_strict(text, SnapshotError),
        expected_world_id=expected_world_id,
        policy=policy,
    )


class SnapshotReader(Protocol):
    """One bounded read of the public snapshot boundary for an explicit world."""

    def read_scheduling_snapshot(self, world_id: str) -> Mapping[str, Any]: ...


class TwinQuery(Protocol):
    """The public Twin query surface (``TwinQueryAPI``); no private store is used."""

    def get_scheduling_snapshot_v1(
        self, context: Any, *, world_id: str
    ) -> Mapping[str, Any]: ...


class TwinSnapshotReader:
    """Thin adapter binding an already-authenticated context to the Twin query API.

    It adds no identity or scope logic: a denied read raises the Twin's own error.
    """

    def __init__(self, api: TwinQuery, context: Any) -> None:
        self._api = api
        self._context = context

    def read_scheduling_snapshot(self, world_id: str) -> Mapping[str, Any]:
        return self._api.get_scheduling_snapshot_v1(self._context, world_id=world_id)


def to_planning_input(snapshot: PlanningSnapshot) -> PlanningInput:
    return PlanningInput(snapshot)


def read_planning_input(
    reader: SnapshotReader, *, world_id: str, policy: FreshnessPolicy
) -> PlanningInput:
    """Read once (no retry, no per-entity calls) and parse for the requested world."""

    world = Reader(SnapshotError).ident(world_id, "world_id")
    payload = reader.read_scheduling_snapshot(world)
    return to_planning_input(
        parse_snapshot(payload, expected_world_id=world, policy=policy)
    )
