"""PostgreSQL-backed persistence for one read-only Twin projection scope.

The caller owns the connection and transaction so projection changes can commit
atomically with the EVT-003 delivery ledger before a broker ACK.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .projector import (
    AdmissionError,
    ApplyResult,
    ProjectionEvent,
    ProjectionGap,
    ProjectionState,
    Projector,
)


def _row_values(row: tuple[Any, ...] | Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(row.values()) if isinstance(row, Mapping) else row


def _fetchone(
    connection: Any,
    query: str,
    parameters: tuple[Any, ...],
) -> tuple[Any, ...] | None:
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        row = cursor.fetchone()
        return _row_values(row) if row is not None else None


def _fetchall(
    connection: Any,
    query: str,
    parameters: tuple[Any, ...],
) -> list[tuple[Any, ...]]:
    with connection.cursor() as cursor:
        cursor.execute(query, parameters)
        return [_row_values(row) for row in cursor.fetchall()]


class PostgresProjectionStore:
    """Persist and restore projector state using the existing ``twin`` schema."""

    def __init__(self, consumer_scope: str) -> None:
        if not isinstance(consumer_scope, str) or not consumer_scope.strip():
            raise ValueError("consumer_scope must be nonblank")
        self.consumer_scope = consumer_scope

    def restore_projector(
        self,
        connection: Any,
        *,
        world_id: str,
        branch_id: str = "PRIMARY",
    ) -> Projector:
        """Restore one world's read model inside the caller's transaction."""
        self._require_transaction(connection)
        return Projector(self._load_state(connection, world_id, branch_id))

    def apply(
        self,
        connection: Any,
        projector: Projector,
        event: ProjectionEvent,
    ) -> ApplyResult:
        """Apply one event and persist its ledger, entity, and revision atomically."""
        self._require_transaction(connection)
        if (
            projector.state.world_id != event.world_id
            or projector.state.branch_id != event.branch_id
        ):
            raise AdmissionError("event scope does not match projection")

        lock_key = json.dumps(
            [self.consumer_scope, event.world_id, event.branch_id],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,)
        )
        state = self._load_state(connection, event.world_id, event.branch_id)
        self._check_replay_identity(connection, event)
        candidate = Projector(state)
        try:
            result = candidate.apply(event)
        except ProjectionGap:
            # Keep this worker's in-memory freshness conservative. The delivery
            # transaction rolls back and is NAKed, so the durable message remains
            # available for reconciliation/redelivery.
            projector.state = candidate.state
            raise

        if result.outcome == "DUPLICATE":
            projector.state = candidate.state
            return result

        entity = candidate.state.entities[(event.aggregate_type, event.aggregate_id)]
        connection.execute(
            """
            INSERT INTO twin.applied_event (
                consumer_scope, event_id, world_id, branch_id,
                aggregate_type, aggregate_id, aggregate_version
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                self.consumer_scope,
                event.event_id,
                event.world_id,
                event.branch_id,
                event.aggregate_type,
                event.aggregate_id,
                event.aggregate_version,
            ),
        )
        connection.execute(
            """
            INSERT INTO twin.projection_entity (
                aggregate_type, aggregate_id, world_id, branch_id,
                aggregate_version, state, source_event_id, source_revision
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (world_id, branch_id, aggregate_type, aggregate_id)
            DO UPDATE SET
                aggregate_version = EXCLUDED.aggregate_version,
                state = EXCLUDED.state,
                source_event_id = EXCLUDED.source_event_id,
                source_revision = EXCLUDED.source_revision,
                updated_at = now()
            """,
            (
                event.aggregate_type,
                event.aggregate_id,
                event.world_id,
                event.branch_id,
                event.aggregate_version,
                json.dumps(entity),
                entity["source_event_id"],
                entity["source_revision"],
            ),
        )
        connection.execute(
            """
            DELETE FROM twin.projection_gap
            WHERE consumer_scope = %s AND world_id = %s AND branch_id = %s
              AND aggregate_type = %s AND aggregate_id = %s
              AND required_version <= %s
            """,
            (
                self.consumer_scope,
                event.world_id,
                event.branch_id,
                event.aggregate_type,
                event.aggregate_id,
                event.aggregate_version,
            ),
        )
        pending_gap = _fetchone(
            connection,
            """
            SELECT 1 FROM twin.projection_gap
            WHERE consumer_scope = %s AND world_id = %s AND branch_id = %s
            LIMIT 1
            """,
            (self.consumer_scope, event.world_id, event.branch_id),
        )
        if pending_gap is not None:
            candidate.state.status = "STALE"
            candidate.state.degraded_reason = "projection gap requires reconciliation"
        else:
            candidate.state.status = "FRESH"
            candidate.state.degraded_reason = None
        connection.execute(
            """
            INSERT INTO twin.projection_revision (
                world_id, branch_id, source_event_id, status
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT (world_id, branch_id)
            DO UPDATE SET
                source_event_id = EXCLUDED.source_event_id,
                status = EXCLUDED.status,
                updated_at = now()
            """,
            (
                event.world_id,
                event.branch_id,
                event.event_id,
                candidate.state.status,
            ),
        )
        projector.state = candidate.state
        return ApplyResult(
            result.outcome,
            result.event_id,
            result.source_revision,
            candidate.state.status,
        )

    def mark_stale(self, connection: Any, event: ProjectionEvent) -> bool:
        """Persist an unresolved sequence gap after its delivery transaction rolls back.

        A gap marker must not claim the rejected event as the current source
        revision. If another delivery closed the gap before this marker obtains
        the scope lock, the projection is left at that newer state instead.
        """
        self._require_transaction(connection)
        lock_key = json.dumps(
            [self.consumer_scope, event.world_id, event.branch_id],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        connection.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,)
        )
        row = _fetchone(
            connection,
            """
            SELECT aggregate_version
            FROM twin.projection_entity
            WHERE world_id = %s AND branch_id = %s
              AND aggregate_type = %s AND aggregate_id = %s
            """,
            (event.world_id, event.branch_id, event.aggregate_type, event.aggregate_id),
        )
        current_version = row[0] if row is not None else 0
        if event.aggregate_version <= current_version + 1:
            return False

        connection.execute(
            """
            INSERT INTO twin.projection_gap (
                consumer_scope, world_id, branch_id, aggregate_type,
                aggregate_id, required_version
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                consumer_scope, world_id, branch_id, aggregate_type, aggregate_id
            ) DO UPDATE SET
                required_version = GREATEST(
                    twin.projection_gap.required_version, EXCLUDED.required_version
                ),
                detected_at = now()
            """,
            (
                self.consumer_scope,
                event.world_id,
                event.branch_id,
                event.aggregate_type,
                event.aggregate_id,
                event.aggregate_version,
            ),
        )
        connection.execute(
            """
            INSERT INTO twin.projection_revision (
                world_id, branch_id, source_event_id, status
            ) VALUES (%s, %s, NULL, 'STALE')
            ON CONFLICT (world_id, branch_id)
            DO UPDATE SET status = 'STALE', updated_at = now()
            """,
            (event.world_id, event.branch_id),
        )
        return True

    @staticmethod
    def _require_transaction(connection: Any) -> None:
        if connection.info.transaction_status.name != "INTRANS":
            raise ValueError("projection persistence requires an active transaction")

    def _check_replay_identity(self, connection: Any, event: ProjectionEvent) -> None:
        row = _fetchone(
            connection,
            """
            SELECT world_id, branch_id, aggregate_type, aggregate_id,
                   aggregate_version
            FROM twin.applied_event
            WHERE consumer_scope = %s AND event_id = %s
            """,
            (self.consumer_scope, event.event_id),
        )
        if row is None:
            return
        identity = (
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
        )
        requested = (
            event.world_id,
            event.branch_id,
            event.aggregate_type,
            event.aggregate_id,
            event.aggregate_version,
        )
        if identity != requested:
            raise AdmissionError("event_id: conflicting replay identity")

    def _load_state(
        self,
        connection: Any,
        world_id: str,
        branch_id: str,
    ) -> ProjectionState:
        if not world_id.strip() or not branch_id.strip():
            raise ValueError("projection world and branch must be nonblank")
        state = ProjectionState(world_id, branch_id)
        rows = _fetchall(
            connection,
            """
            SELECT aggregate_type, aggregate_id, aggregate_version, state
            FROM twin.projection_entity
            WHERE world_id = %s AND branch_id = %s
            ORDER BY aggregate_type, aggregate_id
            """,
            (world_id, branch_id),
        )
        for row in rows:
            aggregate_type, aggregate_id, version, entity = row
            if not isinstance(entity, Mapping):
                raise AdmissionError("projection state: persisted entity is invalid")
            state.entities[(aggregate_type, aggregate_id)] = dict(entity)
            state.aggregate_revisions[(aggregate_type, aggregate_id)] = version

        event_rows = _fetchall(
            connection,
            """
            SELECT event_id, aggregate_version
            FROM twin.applied_event
            WHERE consumer_scope = %s AND world_id = %s AND branch_id = %s
            """,
            (self.consumer_scope, world_id, branch_id),
        )
        state.applied_events = {row[0]: row[1] for row in event_rows}

        revision = _fetchone(
            connection,
            """
            SELECT source_event_id, status
            FROM twin.projection_revision
            WHERE world_id = %s AND branch_id = %s
            """,
            (world_id, branch_id),
        )
        if revision is not None:
            state.source_revision = revision[0]
            state.status = revision[1]
            if state.status == "STALE":
                state.degraded_reason = "persisted projection requires reconciliation"
            elif state.status == "DEGRADED":
                state.degraded_reason = "persisted projection is degraded"
        pending_gap = _fetchone(
            connection,
            """
            SELECT 1 FROM twin.projection_gap
            WHERE consumer_scope = %s AND world_id = %s AND branch_id = %s
            LIMIT 1
            """,
            (self.consumer_scope, world_id, branch_id),
        )
        if pending_gap is not None:
            state.status = "STALE"
            state.degraded_reason = "projection gap requires reconciliation"
        return state
