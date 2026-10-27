"""Versioned, read-only Twin query surface for scheduler consumers.

The Twin is a projection, so this module accepts a provider for its current
projection and returns a defensive copy. It does not assemble canonical
manufacturing state, execute commands, or expose simulator-only Oracle data.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


SCHEDULING_SNAPSHOT_READ = "twin:scheduling-snapshot:read"
_FRESHNESS_STATUSES = frozenset({"FRESH", "DEGRADED", "STALE"})
_MAINTENANCE_STATES = frozenset(
    {"AVAILABLE", "PLANNED_MAINTENANCE", "IN_MAINTENANCE", "UNAVAILABLE"}
)


class SnapshotQueryError(ValueError):
    """The projected snapshot cannot satisfy the versioned query contract."""


class ReadScopeDenied(PermissionError):
    """The authenticated consumer has no approved read scope."""


@dataclass(frozen=True)
class TwinReadContext:
    """Authenticated identity and scopes supplied by the caller boundary."""

    consumer_id: str
    scopes: frozenset[str]


SnapshotProvider = Callable[[str], Mapping[str, Any]]


def _nonblank(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SnapshotQueryError(f"{field}: nonblank string required")
    return value


def _exact_keys(value: Mapping[str, Any], required: set[str], field: str) -> None:
    actual = set(value)
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        raise SnapshotQueryError(
            f"{field}: exact fields required; missing={missing}, extra={extra}"
        )


def _validate_snapshot(snapshot: Mapping[str, Any], expected_world_id: str) -> dict[str, Any]:
    top_level = {
        "contract_version",
        "world_id",
        "snapshot_revision",
        "generated_at",
        "freshness",
        "lots",
        "equipment",
        "current_schedule_version",
    }
    _exact_keys(snapshot, top_level, "snapshot")
    if snapshot["contract_version"] != "core.scheduling-snapshot.v1":
        raise SnapshotQueryError("contract_version: unsupported version")
    if _nonblank(snapshot["world_id"], "world_id") != expected_world_id:
        raise SnapshotQueryError("world_id: query scope mismatch")
    _nonblank(snapshot["snapshot_revision"], "snapshot_revision")
    _nonblank(snapshot["generated_at"], "generated_at")

    freshness = snapshot["freshness"]
    if not isinstance(freshness, Mapping):
        raise SnapshotQueryError("freshness: object required")
    _exact_keys(freshness, {"status", "valid_until"}, "freshness")
    if freshness["status"] not in _FRESHNESS_STATUSES:
        raise SnapshotQueryError("freshness.status: unsupported status")
    _nonblank(freshness["valid_until"], "freshness.valid_until")

    lots = snapshot["lots"]
    if not isinstance(lots, list):
        raise SnapshotQueryError("lots: array required")
    for index, lot in enumerate(lots):
        field = f"lots[{index}]"
        if not isinstance(lot, Mapping):
            raise SnapshotQueryError(f"{field}: object required")
        _exact_keys(
            lot,
            {"id", "revision", "route_position", "priority", "due_at", "eligible_equipment_ids"},
            field,
        )
        _nonblank(lot["id"], f"{field}.id")
        _nonblank(lot["revision"], f"{field}.revision")
        if type(lot["priority"]) is not int or lot["priority"] < 0:
            raise SnapshotQueryError(f"{field}.priority: non-negative integer required")
        _nonblank(lot["due_at"], f"{field}.due_at")
        route = lot["route_position"]
        if not isinstance(route, Mapping):
            raise SnapshotQueryError(f"{field}.route_position: object required")
        _exact_keys(
            route,
            {"route_id", "visit_id", "position", "operation_class_id"},
            f"{field}.route_position",
        )
        for route_field in ("route_id", "visit_id", "operation_class_id"):
            _nonblank(route[route_field], f"{field}.route_position.{route_field}")
        if type(route["position"]) is not int or route["position"] < 0:
            raise SnapshotQueryError(f"{field}.route_position.position: non-negative integer required")
        equipment_ids = lot["eligible_equipment_ids"]
        if not isinstance(equipment_ids, list) or any(
            not isinstance(item, str) or not item.strip() for item in equipment_ids
        ):
            raise SnapshotQueryError(f"{field}.eligible_equipment_ids: nonblank string array required")
        if len(set(equipment_ids)) != len(equipment_ids):
            raise SnapshotQueryError(f"{field}.eligible_equipment_ids: values must be unique")

    equipment = snapshot["equipment"]
    if not isinstance(equipment, list):
        raise SnapshotQueryError("equipment: array required")
    for index, item in enumerate(equipment):
        field = f"equipment[{index}]"
        if not isinstance(item, Mapping):
            raise SnapshotQueryError(f"{field}: object required")
        _exact_keys(item, {"id", "revision", "maintenance_state"}, field)
        _nonblank(item["id"], f"{field}.id")
        _nonblank(item["revision"], f"{field}.revision")
        if item["maintenance_state"] not in _MAINTENANCE_STATES:
            raise SnapshotQueryError(f"{field}.maintenance_state: unsupported state")
    schedule_version = snapshot["current_schedule_version"]
    if schedule_version is not None:
        _nonblank(schedule_version, "current_schedule_version")
    return deepcopy(dict(snapshot))


class TwinQueryAPI:
    """Small versioned query API over one explicitly scoped Twin projection."""

    def __init__(
        self,
        snapshot_provider: SnapshotProvider,
        consumer_scopes: Mapping[str, frozenset[str]],
    ) -> None:
        self._snapshot_provider = snapshot_provider
        self._consumer_scopes = {
            _nonblank(consumer_id, "consumer_id"): frozenset(scopes)
            for consumer_id, scopes in consumer_scopes.items()
        }

    def get_scheduling_snapshot_v1(
        self, context: TwinReadContext, *, world_id: str
    ) -> dict[str, Any]:
        """Return a validated snapshot without granting mutation authority."""

        consumer_id = _nonblank(context.consumer_id, "consumer_id")
        configured = self._consumer_scopes.get(consumer_id)
        if configured is None or SCHEDULING_SNAPSHOT_READ not in configured:
            raise ReadScopeDenied("consumer is not approved for SchedulingSnapshot reads")
        if SCHEDULING_SNAPSHOT_READ not in context.scopes:
            raise ReadScopeDenied("request context lacks SchedulingSnapshot read scope")
        requested_world = _nonblank(world_id, "world_id")
        snapshot = self._snapshot_provider(requested_world)
        return _validate_snapshot(snapshot, requested_world)

