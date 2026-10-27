"""Internal relational history storage. Caller owns authorization/transaction.

No update/delete/upsert path, protected execution, or lifecycle mutation exists.
Route snapshots preserve historical versions without mutating current routes.
"""

import psycopg
from psycopg.rows import DictRow

from manufacturing_core.domain import ManufacturingRoute, RouteVisit
from manufacturing_core.rework import (
    ComponentExecutionHistory,
    ExecutionSegment,
    ProcessExecutionRecord,
    ReworkDirective,
    ReworkExecutionSegment,
)


class ReworkHistoryRepository:
    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def _lock(self, component_id: str) -> None:
        # Serializes this component's create/append paths without granting UPDATE
        # on canonical component rows. Hash collisions only serialize more work.
        self.connection.execute(
            "SELECT pg_catalog.pg_advisory_xact_lock("
            "pg_catalog.hashtextextended('core.rework.history:' || %s, 0))",
            (component_id,),
        )

    def create(self, history: ComponentExecutionHistory) -> None:
        """Insert one complete initial history; an existing history is an error."""
        history = ComponentExecutionHistory.model_validate(history.model_dump())
        with self.connection.transaction():
            self._lock(history.component_id)
            self.connection.execute(
                "INSERT INTO core.rework_history (component_id) VALUES (%s)",
                (history.component_id,),
            )
            self._insert_segment(history.component_id, 0, history.original)
            for position, segment in enumerate(history.rework, 1):
                self._insert_segment(history.component_id, position, segment)

    def append_rework(
        self, component_id: str, segment: ReworkExecutionSegment
    ) -> ComponentExecutionHistory:
        """Append atomically after loading/validating the locked history prefix.

        Nested caller transactions use a savepoint. A failure cannot leave a
        directive, route snapshot or partial execution set behind. The caller's
        outer rollback still rolls back every successful append.
        """
        segment = ReworkExecutionSegment.model_validate(segment.model_dump())
        with self.connection.transaction():
            self._lock(component_id)
            history = self.get(component_id)
            if history is None:
                raise ValueError("component execution history does not exist")
            updated = history.append_rework(segment)
            self._insert_segment(component_id, len(updated.rework), segment)
            return updated

    def _insert_segment(
        self, component_id: str, position: int, segment: ExecutionSegment
    ) -> None:
        directive_id = None
        if isinstance(segment, ReworkExecutionSegment):
            directive = segment.directive
            directive_id = directive.id
            self.connection.execute(
                "INSERT INTO core.rework_directive "
                "(id, revision, component_id, reason, originating_inspection_id, "
                "origin_execution_id, return_visit_id, rework_route_id, "
                "rework_route_revision, related_defect_id, related_incident_id, "
                "current_rework_count, approval_state, policy_state) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    directive.id,
                    directive.revision,
                    directive.component_id,
                    directive.reason,
                    directive.originating_inspection_id,
                    directive.origin_execution_id,
                    directive.return_visit_id,
                    directive.rework_route_id,
                    directive.rework_route_revision,
                    directive.related_defect_id,
                    directive.related_incident_id,
                    directive.current_rework_count,
                    directive.approval_state,
                    directive.policy_state,
                ),
            )
        self.connection.execute(
            "INSERT INTO core.rework_segment "
            "(component_id, position, route_id, route_revision, directive_id) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                component_id,
                position,
                segment.route.id,
                segment.route.revision,
                directive_id,
            ),
        )
        for index, visit in enumerate(segment.route.visits):
            self.connection.execute(
                "INSERT INTO core.rework_route_visit "
                "(component_id, segment_position, position, id, revision, "
                "operation_class_id, equipment_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    component_id,
                    position,
                    index,
                    visit.id,
                    visit.revision,
                    visit.operation_class_id,
                    visit.equipment_id,
                ),
            )
        for index, record in enumerate(segment.executions):
            self.connection.execute(
                "INSERT INTO core.rework_execution "
                "(id, revision, component_id, segment_position, position, lot_id, "
                "route_visit_id, equipment_id, started_at, ended_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    record.id,
                    record.revision,
                    record.component_id,
                    position,
                    index,
                    record.lot_id,
                    record.route_visit_id,
                    record.equipment_id,
                    record.started_at,
                    record.ended_at,
                ),
            )

    def get(self, component_id: str) -> ComponentExecutionHistory | None:
        present = self.connection.execute(
            "SELECT component_id FROM core.rework_history WHERE component_id = %s",
            (component_id,),
        ).fetchone()
        if present is None:
            return None
        rows = self.connection.execute(
            "SELECT position, route_id, route_revision, directive_id "
            "FROM core.rework_segment WHERE component_id = %s ORDER BY position",
            (component_id,),
        ).fetchall()
        original: ExecutionSegment | None = None
        rework: list[ReworkExecutionSegment] = []
        for position, row in enumerate(rows):
            if row["position"] != position:
                raise ValueError("incomplete rework history positions")
            route_rows = self.connection.execute(
                "SELECT id, revision, operation_class_id, equipment_id "
                "FROM core.rework_route_visit "
                "WHERE component_id = %s AND segment_position = %s ORDER BY position",
                (component_id, position),
            ).fetchall()
            route = ManufacturingRoute(
                id=row["route_id"],
                revision=row["route_revision"],
                visits=tuple(
                    RouteVisit(route_id=row["route_id"], **visit)
                    for visit in route_rows
                ),
            )
            execution_rows = self.connection.execute(
                "SELECT id, revision, component_id, lot_id, route_visit_id, "
                "equipment_id, started_at, ended_at FROM core.rework_execution "
                "WHERE component_id = %s AND segment_position = %s ORDER BY position",
                (component_id, position),
            ).fetchall()
            executions = tuple(
                ProcessExecutionRecord.model_validate(r) for r in execution_rows
            )
            if position == 0:
                original = ExecutionSegment(route=route, executions=executions)
            else:
                directive = self.connection.execute(
                    "SELECT * FROM core.rework_directive WHERE id = %s AND component_id = %s",
                    (row["directive_id"], component_id),
                ).fetchone()
                if directive is None:
                    raise ValueError("rework directive is missing")
                directive["current_rework_count"] = int(
                    directive["current_rework_count"]
                )
                rework.append(
                    ReworkExecutionSegment(
                        route=route,
                        executions=executions,
                        directive=ReworkDirective.model_validate(directive),
                    )
                )
        if original is None:
            raise ValueError("original execution segment is missing")
        return ComponentExecutionHistory(
            component_id=component_id, original=original, rework=tuple(rework)
        )
