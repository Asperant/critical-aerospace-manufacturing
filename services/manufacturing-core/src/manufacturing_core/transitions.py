"""WP-CORE-002 canonical transition guards and transactional handlers.

The matrices in this module are the only legal state changes exposed by the
Core transition surface.  They deliberately keep lifecycle, execution and
material-hold state independent.  Rework execution, genealogy, split/merge
records and event publication remain separate work packages.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Set
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any, TypeVar
from uuid import UUID, uuid4

import psycopg
from pydantic import BaseModel, ConfigDict, StringConstraints

from manufacturing_core.command_persistence import PostgresCommandLedger
from manufacturing_core.commands import (
    CommandRejected,
    DispatchLot,
    PlaceLotOnHold,
    ReleaseMaterialHold,
)
from manufacturing_core.enforcement import authorize
from manufacturing_core.events_v1 import (
    EntityReference,
    LotDispatchAuthorizedEvent,
    LotDispatchAuthorizedPayloadV1,
    LotHeldEvent,
    LotHeldPayloadV1,
    UtcOccurrence,
    new_event_id,
    new_trace_id,
)
from manufacturing_core.lifecycle import (
    ExecutionState,
    LotLifecycle,
    LotState,
    ProductionOrderLifecycle,
    SerializedComponentLifecycle,
)
from manufacturing_core.observability import record_transition_rejection
from manufacturing_core.outbox import OutboxRecord

Identity = Annotated[str, StringConstraints(strict=True, pattern=r"^\S+$")]


class MaterialHoldStatus(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class MaterialHold(BaseModel):
    """A retained hold record; RELEASED rows are history, not deletion tombstones."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Identity
    lot_id: Identity
    reason: Annotated[str, StringConstraints(strict=True, min_length=1)]
    status: MaterialHoldStatus = MaterialHoldStatus.ACTIVE
    placed_at: datetime
    released_at: datetime | None = None
    release_reason: str | None = None
    placed_command_id: UUID
    released_command_id: UUID | None = None


class TransitionRejected(CommandRejected):
    """A stable, inspectable rejection code for an illegal domain operation."""


StateT = TypeVar("StateT", bound=StrEnum)


def _matrix(
    values: Mapping[StateT, Collection[StateT]],
) -> Mapping[StateT, frozenset[StateT]]:
    return {key: frozenset(targets) for key, targets in values.items()}


ORDER_TRANSITIONS = _matrix(
    {
        ProductionOrderLifecycle.CREATED: (
            ProductionOrderLifecycle.VALIDATED,
            ProductionOrderLifecycle.CANCELLED,
        ),
        ProductionOrderLifecycle.VALIDATED: (
            ProductionOrderLifecycle.RELEASED,
            ProductionOrderLifecycle.CANCELLED,
            ProductionOrderLifecycle.SUSPENDED,
        ),
        ProductionOrderLifecycle.RELEASED: (
            ProductionOrderLifecycle.IN_PROGRESS,
            ProductionOrderLifecycle.CANCELLED,
            ProductionOrderLifecycle.SUSPENDED,
        ),
        ProductionOrderLifecycle.IN_PROGRESS: (
            ProductionOrderLifecycle.COMPLETED,
            ProductionOrderLifecycle.CANCELLED,
            ProductionOrderLifecycle.SUSPENDED,
        ),
        ProductionOrderLifecycle.SUSPENDED: (
            ProductionOrderLifecycle.IN_PROGRESS,
            ProductionOrderLifecycle.CANCELLED,
        ),
    }
)

LOT_TRANSITIONS = _matrix(
    {
        LotLifecycle.CREATED: (
            LotLifecycle.RELEASED,
            LotLifecycle.CANCELLED,
        ),
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

COMPONENT_TRANSITIONS = _matrix(
    {
        SerializedComponentLifecycle.CREATED: (
            SerializedComponentLifecycle.IN_PRODUCTION,
            SerializedComponentLifecycle.SCRAPPED,
        ),
        SerializedComponentLifecycle.IN_PRODUCTION: (
            SerializedComponentLifecycle.COMPLETED,
            SerializedComponentLifecycle.SCRAPPED,
        ),
    }
)

EXECUTION_TRANSITIONS = _matrix(
    {
        ExecutionState.READY: (ExecutionState.QUEUED,),
        # DispatchLot may atomically reserve and dispatch after its resource
        # validation; a separate reservation step remains legal as well.
        ExecutionState.QUEUED: (ExecutionState.RESERVED, ExecutionState.DISPATCHED),
        ExecutionState.RESERVED: (ExecutionState.DISPATCHED,),
        ExecutionState.DISPATCHED: (ExecutionState.PROCESSING,),
        ExecutionState.PROCESSING: (ExecutionState.STEP_COMPLETED,),
        ExecutionState.STEP_COMPLETED: (ExecutionState.READY,),
    }
)


def _validate(
    current: StrEnum,
    target: StrEnum,
    matrix: Mapping[StrEnum, Set[StrEnum]],
) -> None:
    if current in (
        LotLifecycle.SCRAPPED,
        LotLifecycle.CANCELLED,
        ProductionOrderLifecycle.COMPLETED,
        ProductionOrderLifecycle.CANCELLED,
        SerializedComponentLifecycle.COMPLETED,
        SerializedComponentLifecycle.SCRAPPED,
    ):
        raise TransitionRejected("TERMINAL_STATE", f"{current} cannot transition")
    if target not in matrix.get(current, frozenset()):
        raise TransitionRejected(
            "INVALID_TRANSITION", f"{current} -> {target} is not legal"
        )


def validate_order_transition(
    current: ProductionOrderLifecycle, target: ProductionOrderLifecycle
) -> None:
    _validate(current, target, ORDER_TRANSITIONS)  # type: ignore[arg-type]


def validate_lot_transition(current: LotLifecycle, target: LotLifecycle) -> None:
    _validate(current, target, LOT_TRANSITIONS)  # type: ignore[arg-type]


def validate_component_transition(
    current: SerializedComponentLifecycle, target: SerializedComponentLifecycle
) -> None:
    _validate(current, target, COMPONENT_TRANSITIONS)  # type: ignore[arg-type]


def validate_execution_transition(
    current: ExecutionState, target: ExecutionState
) -> None:
    if target not in EXECUTION_TRANSITIONS.get(current, frozenset()):
        raise TransitionRejected(
            "INVALID_EXECUTION_TRANSITION", f"{current} -> {target} is not legal"
        )


def validate_dispatch(
    execution: ExecutionState,
    *,
    active_hold: bool,
    resource_available: bool,
) -> None:
    if execution is not ExecutionState.QUEUED:
        raise TransitionRejected("DISPATCH_REQUIRES_QUEUED", "lot is not queued")
    if active_hold:
        raise TransitionRejected("ACTIVE_HOLD", "active material hold blocks dispatch")
    if not resource_available:
        raise TransitionRejected("RESOURCE_UNAVAILABLE", "resource is not available")


def validate_process_start(
    execution: ExecutionState, *, resource_available: bool
) -> None:
    if execution is not ExecutionState.DISPATCHED:
        raise TransitionRejected(
            "PROCESS_START_REQUIRES_DISPATCH", "execution was not dispatched"
        )
    if not resource_available:
        raise TransitionRejected("RESOURCE_UNAVAILABLE", "resource is not available")


def validate_rework(
    lifecycle: LotLifecycle | SerializedComponentLifecycle,
    *,
    has_directive: bool,
    governed_reopen: bool = False,
) -> None:
    if not has_directive:
        raise TransitionRejected(
            "REWORK_DIRECTIVE_REQUIRED", "rework requires an explicit directive"
        )
    if lifecycle in (LotLifecycle.SCRAPPED, SerializedComponentLifecycle.SCRAPPED):
        raise TransitionRejected(
            "TERMINAL_STATE", "scrapped material cannot be reworked"
        )
    if (
        lifecycle in (LotLifecycle.COMPLETED, SerializedComponentLifecycle.COMPLETED)
        and not governed_reopen
    ):
        raise TransitionRejected(
            "REWORK_REOPEN_REQUIRED", "completed material needs governed reopen"
        )


class TransitionRepository:
    """Small mutation surface used inside the command-ledger transaction."""

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.connection = connection

    def lot_revision(self, lot_id: str, *, for_update: bool = False) -> str | None:
        suffix = " FOR UPDATE" if for_update else ""
        row = self.connection.execute(
            "SELECT revision FROM core.lot WHERE id = %s" + suffix, (lot_id,)
        ).fetchone()
        return None if row is None else row["revision"]

    def lot_state(self, lot_id: str, *, for_update: bool = False) -> LotState | None:
        suffix = " FOR UPDATE" if for_update else ""
        row = self.connection.execute(
            "SELECT id, revision, lifecycle_state, execution_state "
            "FROM core.lot_state WHERE id = %s" + suffix,
            (lot_id,),
        ).fetchone()
        return None if row is None else LotState.model_validate(row)

    def next_lot_event_version(self, lot_id: str) -> int:
        """Allocate a per-lot event version without changing opaque revisions."""
        self.connection.execute(
            "INSERT INTO core.lot_event_sequence (lot_id) VALUES (%s) "
            "ON CONFLICT (lot_id) DO NOTHING",
            (lot_id,),
        )
        row = self.connection.execute(
            "UPDATE core.lot_event_sequence SET next_version = next_version + 1 "
            "WHERE lot_id = %s RETURNING next_version",
            (lot_id,),
        ).fetchone()
        if row is None:
            raise TransitionRejected(
                "EVENT_VERSION_UNAVAILABLE", "lot event sequence missing"
            )
        return row["next_version"]

    def active_hold(
        self, lot_id: str, *, for_update: bool = False
    ) -> MaterialHold | None:
        suffix = " FOR UPDATE" if for_update else ""
        row = self.connection.execute(
            "SELECT id, lot_id, reason, status, placed_at, released_at, "
            "release_reason, placed_command_id, released_command_id "
            "FROM core.material_hold WHERE lot_id = %s AND status = 'ACTIVE'" + suffix,
            (lot_id,),
        ).fetchone()
        return None if row is None else MaterialHold.model_validate(row)

    def hold(self, hold_id: str, *, for_update: bool = False) -> MaterialHold | None:
        suffix = " FOR UPDATE" if for_update else ""
        row = self.connection.execute(
            "SELECT id, lot_id, reason, status, placed_at, released_at, "
            "release_reason, placed_command_id, released_command_id "
            "FROM core.material_hold WHERE id = %s" + suffix,
            (hold_id,),
        ).fetchone()
        return None if row is None else MaterialHold.model_validate(row)

    def _new_revision(self) -> str:
        return uuid4().hex

    def transition_lot(
        self, lot_id: str, target: LotLifecycle, expected_revision: str
    ) -> None:
        current = self.lot_state(lot_id, for_update=True)
        if current is None:
            raise TransitionRejected("NOT_FOUND", "lot does not exist")
        if current.revision != expected_revision:
            raise TransitionRejected("STALE", "lot revision changed")
        validate_lot_transition(current.lifecycle_state, target)
        revision = self._new_revision()
        self.connection.execute(
            "UPDATE core.lot SET revision = %s WHERE id = %s AND revision = %s",
            (revision, lot_id, expected_revision),
        )
        self.connection.execute(
            "UPDATE core.lot_state SET revision = %s, lifecycle_state = %s "
            "WHERE id = %s AND revision = %s",
            (revision, target.value, lot_id, expected_revision),
        )

    def place_hold(
        self,
        command: PlaceLotOnHold,
        *,
        expected_revision: str | None,
        now: datetime | None = None,
    ) -> OutboxRecord:
        if command.target.entity_type != "Lot":
            raise TransitionRejected("INVALID_TARGET", "hold target must be a lot")
        lot_id = command.target.entity_id
        revision = self.lot_revision(lot_id, for_update=True)
        if revision is None:
            raise TransitionRejected("NOT_FOUND", "lot does not exist")
        if expected_revision is not None and revision != expected_revision:
            raise TransitionRejected("STALE", "lot revision changed")
        if self.active_hold(lot_id, for_update=True) is not None:
            raise TransitionRejected(
                "HOLD_ALREADY_ACTIVE", "lot already has an active hold"
            )
        timestamp = now or datetime.now(UTC)
        try:
            self.connection.execute(
                "INSERT INTO core.material_hold "
                "(id, lot_id, reason, status, placed_at, placed_command_id) "
                "VALUES (%s, %s, %s, 'ACTIVE', %s, %s)",
                (
                    command.material_hold_id,
                    lot_id,
                    command.hold_reason,
                    timestamp,
                    str(command.command_id),
                ),
            )
        except psycopg.errors.UniqueViolation as error:
            raise TransitionRejected(
                "HOLD_ID_CONFLICT", "hold identity is already used"
            ) from error
        event_version = self.next_lot_event_version(lot_id)
        event = LotHeldEvent(
            event_id=new_event_id(),
            producer="manufacturing-core",
            world_id=command.world_id,
            correlation_id=command.correlation_id,
            causation_id=str(command.command_id),
            trace_id=new_trace_id(),
            occurred_at=UtcOccurrence(clock="UTC", value=timestamp),
            observed_at=timestamp,
            entity_refs=(
                EntityReference(entity_type="Lot", id=lot_id, revision=revision),
            ),
            event_type="production.lot-held",
            schema_version=1,
            payload=LotHeldPayloadV1(
                event_type="production.lot-held",
                schema_version=1,
                aggregate_type="Lot",
                aggregate_id=lot_id,
                aggregate_version=event_version,
                lot_id=lot_id,
                lot_revision=revision,
                material_hold_id=command.material_hold_id,
                reason=command.hold_reason,
            ),
        )
        return OutboxRecord.new(event, created_at=timestamp)

    def release_hold(
        self,
        command: ReleaseMaterialHold,
        *,
        expected_revision: str | None,
        now: datetime | None = None,
    ) -> None:
        if command.target.entity_type != "Lot":
            raise TransitionRejected("INVALID_TARGET", "release target must be a lot")
        revision = self.lot_revision(command.target.entity_id, for_update=True)
        if revision is None:
            raise TransitionRejected("NOT_FOUND", "lot does not exist")
        if expected_revision is not None and revision != expected_revision:
            raise TransitionRejected("STALE", "lot revision changed")
        hold = self.hold(command.hold_id, for_update=True)
        if hold is None:
            raise TransitionRejected("HOLD_NOT_FOUND", "hold does not exist")
        if hold.lot_id != command.target.entity_id:
            raise TransitionRejected(
                "HOLD_TARGET_MISMATCH", "hold belongs to another lot"
            )
        if hold.status is not MaterialHoldStatus.ACTIVE:
            raise TransitionRejected("HOLD_NOT_ACTIVE", "hold is already released")
        timestamp = now or datetime.now(UTC)
        self.connection.execute(
            "UPDATE core.material_hold SET status = 'RELEASED', released_at = %s, "
            "release_reason = %s, released_command_id = %s WHERE id = %s AND status = 'ACTIVE'",
            (
                timestamp,
                command.release_reason,
                str(command.command_id),
                command.hold_id,
            ),
        )

    def dispatch(
        self,
        command: DispatchLot,
        *,
        expected_revision: str | None,
        resource_available: bool,
        now: datetime | None = None,
    ) -> OutboxRecord:
        if command.target.entity_type != "Lot":
            raise TransitionRejected("INVALID_TARGET", "dispatch target must be a lot")
        lot_id = command.target.entity_id
        state = self.lot_state(lot_id, for_update=True)
        if state is None:
            raise TransitionRejected("NOT_FOUND", "lot does not exist")
        if expected_revision is not None and state.revision != expected_revision:
            raise TransitionRejected("STALE", "lot revision changed")
        validate_dispatch(
            state.execution_state,
            active_hold=self.active_hold(lot_id, for_update=True) is not None,
            resource_available=resource_available,
        )
        revision = self._new_revision()
        self.connection.execute(
            "UPDATE core.lot SET revision = %s WHERE id = %s AND revision = %s",
            (revision, lot_id, state.revision),
        )
        self.connection.execute(
            "UPDATE core.lot_state SET revision = %s, execution_state = 'DISPATCHED' "
            "WHERE id = %s AND revision = %s",
            (revision, lot_id, state.revision),
        )
        event_version = self.next_lot_event_version(lot_id)
        timestamp = now or datetime.now(UTC)
        event = LotDispatchAuthorizedEvent(
            event_id=new_event_id(),
            producer="manufacturing-core",
            world_id=command.world_id,
            correlation_id=command.correlation_id,
            causation_id=str(command.command_id),
            trace_id=new_trace_id(),
            occurred_at=UtcOccurrence(clock="UTC", value=timestamp),
            observed_at=timestamp,
            entity_refs=(
                EntityReference(entity_type="Lot", id=lot_id, revision=revision),
            ),
            event_type="production.lot-dispatch-authorized",
            schema_version=1,
            payload=LotDispatchAuthorizedPayloadV1(
                event_type="production.lot-dispatch-authorized",
                schema_version=1,
                aggregate_type="Lot",
                aggregate_id=lot_id,
                aggregate_version=event_version,
                lot_id=lot_id,
                lot_revision=revision,
                dispatch_id=str(command.command_id),
            ),
        )
        return OutboxRecord.new(event, created_at=timestamp)


class CoreTransitionService:
    """Authorized command entrypoints; acceptance and mutation share one transaction."""

    def __init__(self, connection: psycopg.Connection[Any]) -> None:
        self.repository = TransitionRepository(connection)
        self.ledger = PostgresCommandLedger(connection)

    @staticmethod
    def _log_rejection(
        command: PlaceLotOnHold | ReleaseMaterialHold | DispatchLot,
        outcome: Any,
    ) -> Any:
        if outcome.status.value == "REJECTED" and outcome.error_code is not None:
            record_transition_rejection(
                command.correlation_id,
                str(command.command_id),
                f"command.{command.command_type.value}",
                outcome.error_code,
            )
        return outcome

    def place_lot_on_hold(
        self,
        permissions: Collection[str] | None,
        command: PlaceLotOnHold,
        *,
        now: datetime | None = None,
        expected_world_id: str | None = None,
    ):
        authorize(permissions, "PlaceLotOnHold")
        return self._log_rejection(
            command,
            self.ledger.accept(
                command,
                current_revision=self.repository.lot_revision(command.target.entity_id),
                expected_world_id=expected_world_id,
                mutate=lambda: self.repository.place_hold(
                    command,
                    expected_revision=command.expected.expected_revision,
                    now=now,
                ),
                emit=lambda record: record,
            ),
        )

    def release_material_hold(
        self,
        permissions: Collection[str] | None,
        command: ReleaseMaterialHold,
        *,
        now: datetime | None = None,
        expected_world_id: str | None = None,
    ):
        authorize(permissions, "ReleaseMaterialHold")
        return self._log_rejection(
            command,
            self.ledger.accept(
                command,
                current_revision=self.repository.lot_revision(command.target.entity_id),
                expected_world_id=expected_world_id,
                mutate=lambda: self.repository.release_hold(
                    command,
                    expected_revision=command.expected.expected_revision,
                    now=now,
                ),
            ),
        )

    def dispatch_lot(
        self,
        permissions: Collection[str] | None,
        command: DispatchLot,
        *,
        resource_available: bool,
        now: datetime | None = None,
        expected_world_id: str | None = None,
    ):
        return self._log_rejection(
            command,
            self.ledger.accept(
                command,
                current_revision=self.repository.lot_revision(command.target.entity_id),
                expected_world_id=expected_world_id,
                mutate=lambda: self.repository.dispatch(
                    command,
                    expected_revision=command.expected.expected_revision,
                    resource_available=resource_available,
                    now=now,
                ),
                emit=lambda record: record,
            ),
        )
