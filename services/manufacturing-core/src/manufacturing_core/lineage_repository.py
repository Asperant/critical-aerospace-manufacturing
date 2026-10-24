"""Append-only internal lineage snapshots; caller owns authorization/transaction.

One complete closure per world, matching LotLineageHistory's identity. Canonical
lot/component references must already exist; no current membership is changed.
"""

import psycopg
from psycopg.rows import DictRow

from manufacturing_core.lineage import (
    LotLineageEvent,
    LotLineageHistory,
    LotMembershipSnapshot,
)


class LotLineageRepository:
    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def _lock(self, world_id: str) -> None:
        self.connection.execute(
            "SELECT pg_catalog.pg_advisory_xact_lock("
            "pg_catalog.hashtextextended('core.lineage.history:' || %s, 0))",
            (world_id,),
        )

    def create(self, history: LotLineageHistory) -> None:
        """Validate and atomically insert a complete closure, never overwrite."""
        history = LotLineageHistory.model_validate(history.model_dump())
        with self.connection.transaction():
            self._lock(history.world_id)
            self.connection.execute(
                "INSERT INTO core.lineage_history (world_id) VALUES (%s)",
                (history.world_id,),
            )
            # All event and lot rows precede edges: supplied order need not be
            # topological. Positions preserve delivery order without inventing time.
            for position, event in enumerate(history.events):
                self._insert_event(event, position)
            for position, root in enumerate(history.roots):
                self._insert_lot(root, position, None, None)
            for event in history.events:
                self._insert_children(event)
            for event in history.events:
                self._insert_parents(event)

    def append(self, world_id: str, event: LotLineageEvent) -> LotLineageHistory:
        """Validate against a locked prefix and insert only the new fact."""
        event = LotLineageEvent.model_validate(event.model_dump())
        with self.connection.transaction():
            self._lock(world_id)
            history = self.get(world_id)
            if history is None:
                raise ValueError("lineage history does not exist")
            updated = history.append(event)
            self._insert_event(event, len(history.events))
            self._insert_children(event)
            self._insert_parents(event)
            return updated

    def _insert_event(self, event: LotLineageEvent, position: int) -> None:
        self.connection.execute(
            "INSERT INTO core.lineage_event "
            "(world_id, id, revision, position, kind, source_event_id, reason, "
            "occurred_at, effective_from, recorded_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                event.world_id,
                event.id,
                event.revision,
                position,
                event.kind,
                event.source_event_id,
                event.reason,
                event.occurred_at,
                event.effective_from,
                event.recorded_at,
            ),
        )

    def _insert_lot(
        self,
        lot: LotMembershipSnapshot,
        root_position: int | None,
        producer_id: str | None,
        child_position: int | None,
    ) -> None:
        self.connection.execute(
            "INSERT INTO core.lineage_lot "
            "(world_id, lot_id, root_position, producer_id, child_position) "
            "VALUES (%s, %s, %s, %s, %s)",
            (lot.world_id, lot.lot_id, root_position, producer_id, child_position),
        )
        for position, component in enumerate(lot.component_ids):
            self.connection.execute(
                "INSERT INTO core.lineage_membership "
                "(world_id, lot_id, position, component_id) VALUES (%s, %s, %s, %s)",
                (lot.world_id, lot.lot_id, position, component),
            )

    def _insert_children(self, event: LotLineageEvent) -> None:
        for position, child in enumerate(event.children):
            self._insert_lot(child, None, event.id, position)

    def _insert_parents(self, event: LotLineageEvent) -> None:
        for position, parent in enumerate(event.parent_lot_ids):
            self.connection.execute(
                "INSERT INTO core.lineage_parent "
                "(world_id, event_id, position, lot_id) VALUES (%s, %s, %s, %s)",
                (event.world_id, event.id, position, parent),
            )

    def _lot(self, world_id: str, lot_id: str) -> LotMembershipSnapshot:
        rows = self.connection.execute(
            "SELECT component_id FROM core.lineage_membership "
            "WHERE world_id = %s AND lot_id = %s ORDER BY position",
            (world_id, lot_id),
        ).fetchall()
        return LotMembershipSnapshot(
            world_id=world_id,
            lot_id=lot_id,
            component_ids=tuple(row["component_id"] for row in rows),
        )

    def get(self, world_id: str) -> LotLineageHistory | None:
        present = self.connection.execute(
            "SELECT world_id FROM core.lineage_history WHERE world_id = %s",
            (world_id,),
        ).fetchone()
        if present is None:
            return None
        # Capture the event prefix before subsequent reads. Concurrent appends
        # cannot change roots or any facts belonging to this captured prefix.
        rows = self.connection.execute(
            "SELECT id, revision, kind, source_event_id, reason, occurred_at, "
            "effective_from, recorded_at FROM core.lineage_event "
            "WHERE world_id = %s ORDER BY position",
            (world_id,),
        ).fetchall()
        roots = self.connection.execute(
            "SELECT lot_id FROM core.lineage_lot WHERE world_id = %s "
            "AND root_position IS NOT NULL ORDER BY root_position",
            (world_id,),
        ).fetchall()
        events: list[LotLineageEvent] = []
        for row in rows:
            parents = self.connection.execute(
                "SELECT lot_id FROM core.lineage_parent "
                "WHERE world_id = %s AND event_id = %s ORDER BY position",
                (world_id, row["id"]),
            ).fetchall()
            children = self.connection.execute(
                "SELECT lot_id FROM core.lineage_lot "
                "WHERE world_id = %s AND producer_id = %s ORDER BY child_position",
                (world_id, row["id"]),
            ).fetchall()
            events.append(
                LotLineageEvent(
                    **row,
                    world_id=world_id,
                    parent_lot_ids=tuple(p["lot_id"] for p in parents),
                    children=tuple(self._lot(world_id, c["lot_id"]) for c in children),
                )
            )
        return LotLineageHistory(
            world_id=world_id,
            roots=tuple(self._lot(world_id, root["lot_id"]) for root in roots),
            events=tuple(events),
        )
