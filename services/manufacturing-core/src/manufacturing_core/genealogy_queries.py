"""Controlled, transport-free reads over stored WP-CORE-004 facts.

Caller owns authorization and transaction isolation. Lineage is world-scoped;
execution storage uses globally unique canonical component IDs and has no world
binding yet. These reads do not certify producer completeness or current state.
"""

from collections.abc import Callable
from datetime import UTC
from functools import wraps
from time import perf_counter
from typing import Literal, LiteralString, ParamSpec, Self, TypeVar

import psycopg
from psycopg import sql
from psycopg.rows import DictRow
from pydantic import AwareDatetime, BaseModel, ConfigDict, model_validator

from manufacturing_core.domain import Identity
from manufacturing_core.lineage import LotLineageEvent, LotMembershipSnapshot
from manufacturing_core.observability import CoreHealth, correlation, record
from manufacturing_core.rework import ComponentExecutionHistory, ProcessExecutionRecord
from manufacturing_core.rework_repository import ReworkHistoryRepository

P = ParamSpec("P")
R = TypeVar("R")


def observed(operation: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def call(*args: P.args, **kwargs: P.kwargs) -> R:
            value = kwargs.get("correlation_id")
            if value is not None and not isinstance(value, str):
                raise ValueError("invalid correlation ID")
            identity = correlation(value)
            started = perf_counter()
            try:
                result = function(*args, **kwargs)
            except Exception:
                record(identity, operation, "FAILED", (perf_counter() - started) * 1000)
                raise
            record(identity, operation, "SUCCESS", (perf_counter() - started) * 1000)
            return result

        return call

    return decorate


class QueryValue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LotTraceRequest(QueryValue):
    world_id: Identity
    lot_id: Identity
    direction: Literal["BACKWARD", "FORWARD"] = "BACKWARD"


class ComponentTraceRequest(QueryValue):
    world_id: Identity
    component_id: Identity


class StoredLineageFact(QueryValue):
    position: int
    event: LotLineageEvent


class MaterialTrace(QueryValue):
    world_id: Identity
    focus_lot_ids: tuple[Identity, ...]
    direction: Literal["BACKWARD", "FORWARD"]
    lots: tuple[LotMembershipSnapshot, ...]
    events: tuple[StoredLineageFact, ...]


class EquipmentExposureRequest(QueryValue):
    equipment_id: Identity
    started_at: AwareDatetime
    ended_at: AwareDatetime
    operation_class_id: Identity | None = None

    @model_validator(mode="after")
    def valid_window(self) -> Self:
        if self.ended_at.astimezone(UTC) <= self.started_at.astimezone(UTC):
            raise ValueError("exposure window must be nonempty and increasing")
        return self


class CohortExposureRequest(QueryValue):
    component_ids: tuple[Identity, ...]

    @model_validator(mode="after")
    def distinct_nonempty_cohort(self) -> Self:
        if not self.component_ids or len(set(self.component_ids)) != len(
            self.component_ids
        ):
            raise ValueError("cohort must be nonempty with distinct component IDs")
        return self


class EquipmentCohortExposure(QueryValue):
    equipment_id: Identity
    operation_class_id: Identity
    component_ids: tuple[Identity, ...]
    affected_count: int
    affected_ratio: float
    execution_ids: tuple[Identity, ...]


class CohortExposureResult(QueryValue):
    requested_component_ids: tuple[Identity, ...]
    missing_history_ids: tuple[Identity, ...]
    exposures: tuple[EquipmentCohortExposure, ...]


class ExecutionExposure(QueryValue):
    segment_position: int
    execution_position: int
    execution: ProcessExecutionRecord
    route_id: Identity
    route_revision: Identity
    operation_class_id: Identity
    directive_id: Identity | None


class GenealogyQueries:
    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def health(self, *, correlation_id: str | None = None) -> CoreHealth:
        """Read-access health only; READY does not certify integrated completeness."""
        identity = correlation(correlation_id)
        started = perf_counter()
        status: Literal["READY", "UNAVAILABLE"] = "UNAVAILABLE"
        try:
            row = self.connection.execute(
                "SELECT bool_and(coalesce(pg_catalog.has_table_privilege("
                "current_user, pg_catalog.to_regclass('core.' || name), 'SELECT'), false)) AS ready "
                "FROM unnest(%s::text[]) AS name",
                (
                    [
                        "rework_history",
                        "rework_directive",
                        "rework_segment",
                        "rework_route_visit",
                        "rework_execution",
                        "lineage_history",
                        "lineage_event",
                        "lineage_lot",
                        "lineage_membership",
                        "lineage_parent",
                    ],
                ),
            ).fetchone()
            if row is not None and row["ready"]:
                status = "READY"
        except psycopg.Error:
            # Caller retains transaction recovery; no retry or fabricated empties.
            pass
        record(identity, "genealogy.health", status, (perf_counter() - started) * 1000)
        return CoreHealth(status, identity)

    @observed("genealogy.rework")
    def rework_history(
        self, component_id: str, *, correlation_id: str | None = None
    ) -> ComponentExecutionHistory | None:
        """Return stored append/visit order and exact route/directive snapshots.

        None means no stored history, including known components without history;
        it is never evidence that a component has no prior manufacturing activity.
        """
        return ReworkHistoryRepository(self.connection).get(component_id)

    @observed("genealogy.lot")
    def lot(
        self, request: LotTraceRequest, *, correlation_id: str | None = None
    ) -> MaterialTrace | None:
        request = LotTraceRequest.model_validate(request.model_dump())
        return self._trace(request.world_id, (request.lot_id,), request.direction)

    @observed("genealogy.component")
    def component(
        self, request: ComponentTraceRequest, *, correlation_id: str | None = None
    ) -> MaterialTrace | None:
        """Trace every stored membership of the unchanged component identity.

        Complete merge facts retain the other parents as ancestry context, not
        as evidence that the target component occupied those other parent lots.
        Execution history is separately addressed by its global canonical ID.
        """
        request = ComponentTraceRequest.model_validate(request.model_dump())
        rows = self.connection.execute(
            "SELECT lot_id FROM core.lineage_membership "
            "WHERE world_id = %s AND component_id = %s",
            (request.world_id, request.component_id),
        ).fetchall()
        return self._trace(
            request.world_id, tuple(sorted(row["lot_id"] for row in rows)), "BACKWARD"
        )

    def _trace(
        self,
        world_id: str,
        seeds: tuple[str, ...],
        direction: Literal["BACKWARD", "FORWARD"],
    ) -> MaterialTrace | None:
        step: LiteralString
        if direction == "BACKWARD":
            step = (
                "SELECT p.lot_id FROM reached r "
                "JOIN core.lineage_lot c ON c.world_id = %s AND c.lot_id = r.lot_id "
                "JOIN core.lineage_parent p ON p.world_id = c.world_id "
                "AND p.event_id = c.producer_id"
            )
        else:
            step = (
                "SELECT c.lot_id FROM reached r "
                "JOIN core.lineage_parent p ON p.world_id = %s AND p.lot_id = r.lot_id "
                "JOIN core.lineage_lot c ON c.world_id = p.world_id "
                "AND c.producer_id = p.event_id"
            )
        # UNION deduplicates diamonds; no arbitrary depth cap truncates ancestry.
        # Event IDs are captured in the same statement snapshot as traversal.
        reached = self.connection.execute(
            sql.SQL(
                "WITH RECURSIVE reached(lot_id) AS ("
                "SELECT lot_id FROM core.lineage_lot "
                "WHERE world_id = %s AND lot_id = ANY(%s) UNION {}"
                ") SELECT l.lot_id, l.producer_id, ARRAY("
                "SELECT p.event_id FROM core.lineage_parent p "
                "WHERE p.world_id = l.world_id AND p.lot_id = l.lot_id"
                ") AS consumers FROM reached r JOIN core.lineage_lot l "
                "ON l.world_id = %s AND l.lot_id = r.lot_id"
            ).format(sql.SQL(step)),
            (world_id, list(seeds), world_id, world_id),
        ).fetchall()
        if not reached:
            return None
        event_ids = (
            {r["producer_id"] for r in reached if r["producer_id"] is not None}
            if direction == "BACKWARD"
            else {event for r in reached for event in r["consumers"]}
        )
        events = self.connection.execute(
            "SELECT * FROM core.lineage_event WHERE world_id = %s AND id = ANY(%s)",
            (world_id, sorted(event_ids)),
        ).fetchall()
        parents = self.connection.execute(
            "SELECT event_id, lot_id FROM core.lineage_parent "
            "WHERE world_id = %s AND event_id = ANY(%s) ORDER BY position",
            (world_id, sorted(event_ids)),
        ).fetchall()
        children = self.connection.execute(
            "SELECT producer_id, lot_id FROM core.lineage_lot "
            "WHERE world_id = %s AND producer_id = ANY(%s) ORDER BY child_position",
            (world_id, sorted(event_ids)),
        ).fetchall()
        lot_ids = {r["lot_id"] for r in (*reached, *parents, *children)}
        memberships = self.connection.execute(
            "SELECT lot_id, component_id FROM core.lineage_membership "
            "WHERE world_id = %s AND lot_id = ANY(%s) ORDER BY position",
            (world_id, sorted(lot_ids)),
        ).fetchall()
        lots = {
            lot: LotMembershipSnapshot(
                world_id=world_id,
                lot_id=lot,
                component_ids=tuple(
                    m["component_id"] for m in memberships if m["lot_id"] == lot
                ),
            )
            for lot in sorted(lot_ids)
        }
        facts = []
        for row in events:
            position = row.pop("position")
            facts.append(
                StoredLineageFact(
                    position=position,
                    event=LotLineageEvent(
                        **row,
                        parent_lot_ids=tuple(
                            p["lot_id"] for p in parents if p["event_id"] == row["id"]
                        ),
                        children=tuple(
                            lots[c["lot_id"]]
                            for c in children
                            if c["producer_id"] == row["id"]
                        ),
                    ),
                )
            )
        # Causal topological ordering; occurrence/effectivity/ID break ties only
        # between ready facts. Recording time and delivery position never reorder
        # ancestry. Stored positions remain explicit and unchanged in the result.
        pending = {fact.event.id: fact for fact in facts}
        produced = {c.lot_id: f.event.id for f in facts for c in f.event.children}
        ordered: list[StoredLineageFact] = []
        while pending:
            ready = [
                f
                for f in pending.values()
                if all(
                    produced.get(parent) not in pending
                    for parent in f.event.parent_lot_ids
                )
            ]
            if not ready:
                raise ValueError("cyclic stored lineage")
            fact = min(
                ready,
                key=lambda f: (
                    f.event.occurred_at.astimezone(UTC),
                    f.event.effective_from.astimezone(UTC),
                    f.event.id,
                ),
            )
            ordered.append(fact)
            del pending[fact.event.id]
        return MaterialTrace(
            world_id=world_id,
            focus_lot_ids=tuple(sorted(set(seeds) & lot_ids)),
            direction=direction,
            lots=tuple(lots.values()),
            events=tuple(ordered),
        )

    @observed("genealogy.equipment-exposure")
    def equipment_exposure(
        self, request: EquipmentExposureRequest, *, correlation_id: str | None = None
    ) -> tuple[ExecutionExposure, ...]:
        """Actual executions overlapping [start,end); never planned assignments.

        Zero-duration visits are instants included at start and excluded at end.
        No world filter is invented for the existing world-less execution store.
        """
        request = EquipmentExposureRequest.model_validate(request.model_dump())
        rows = self.connection.execute(
            "SELECT e.id, e.revision, e.component_id, e.lot_id, e.route_visit_id, "
            "e.equipment_id, e.started_at, e.ended_at, e.segment_position, "
            "e.position AS execution_position, s.route_id, s.route_revision, "
            "s.directive_id, v.operation_class_id FROM core.rework_execution e "
            "JOIN core.rework_segment s ON s.component_id = e.component_id "
            "AND s.position = e.segment_position "
            "JOIN core.rework_route_visit v ON v.component_id = e.component_id "
            "AND v.segment_position = e.segment_position AND v.id = e.route_visit_id "
            "WHERE e.equipment_id = %s AND e.started_at < %s AND "
            "(e.ended_at > %s OR (e.started_at = e.ended_at AND e.started_at >= %s)) "
            "AND (%s::text IS NULL OR v.operation_class_id = %s)",
            (
                request.equipment_id,
                request.ended_at,
                request.started_at,
                request.started_at,
                request.operation_class_id,
                request.operation_class_id,
            ),
        ).fetchall()
        result = []
        for row in rows:
            metadata = {
                k: row.pop(k)
                for k in (
                    "segment_position",
                    "execution_position",
                    "route_id",
                    "route_revision",
                    "directive_id",
                    "operation_class_id",
                )
            }
            result.append(
                ExecutionExposure(
                    **metadata, execution=ProcessExecutionRecord.model_validate(row)
                )
            )
        return tuple(
            sorted(
                result,
                key=lambda r: (
                    r.execution.started_at.astimezone(UTC),
                    r.execution.ended_at.astimezone(UTC),
                    r.execution.component_id,
                    r.segment_position,
                    r.execution_position,
                    r.execution.id,
                ),
            )
        )

    @observed("genealogy.common-equipment-exposure")
    def common_equipment_exposure(
        self,
        request: CohortExposureRequest,
        *,
        correlation_id: str | None = None,
    ) -> CohortExposureResult:
        """Deterministic cohort counts over actual visits, not visit counts.

        The denominator is the requested distinct cohort; missing history is
        explicit and must not be treated as verified absence of exposure.
        """
        request = CohortExposureRequest.model_validate(request.model_dump())
        ids = sorted(request.component_ids)
        rows = self.connection.execute(
            "SELECT e.equipment_id, v.operation_class_id, e.component_id, e.id "
            "FROM core.rework_execution e JOIN core.rework_route_visit v "
            "ON v.component_id = e.component_id AND v.segment_position = e.segment_position "
            "AND v.id = e.route_visit_id WHERE e.component_id = ANY(%s)",
            (ids,),
        ).fetchall()
        known = {row["component_id"] for row in rows}
        groups = sorted({(r["equipment_id"], r["operation_class_id"]) for r in rows})
        exposures = []
        for equipment, operation in groups:
            visits = [
                r
                for r in rows
                if (r["equipment_id"], r["operation_class_id"])
                == (equipment, operation)
            ]
            components = tuple(sorted({r["component_id"] for r in visits}))
            exposures.append(
                EquipmentCohortExposure(
                    equipment_id=equipment,
                    operation_class_id=operation,
                    component_ids=components,
                    affected_count=len(components),
                    affected_ratio=len(components) / len(ids),
                    execution_ids=tuple(sorted(r["id"] for r in visits)),
                )
            )
        return CohortExposureResult(
            requested_component_ids=tuple(ids),
            missing_history_ids=tuple(sorted(set(ids) - known)),
            exposures=tuple(exposures),
        )
