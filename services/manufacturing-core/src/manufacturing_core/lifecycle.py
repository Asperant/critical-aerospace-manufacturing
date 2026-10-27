"""WP-CORE-009 canonical lifecycle and execution-state values.

This module deliberately represents state, but does not implement transition
legality.  Transition rules belong to WP-CORE-002.  The state records retain
the immutable identity and revision supplied by the WP-CORE-001 domain
contracts; execution state is an independent dimension from lifecycle state.
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from manufacturing_core.domain import Identity, Revision


class ProductionOrderLifecycle(StrEnum):
    CREATED = "CREATED"
    VALIDATED = "VALIDATED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"


class LotLifecycle(StrEnum):
    CREATED = "CREATED"
    RELEASED = "RELEASED"
    IN_PRODUCTION = "IN_PRODUCTION"
    COMPLETED = "COMPLETED"
    SCRAPPED = "SCRAPPED"
    CANCELLED = "CANCELLED"


class SerializedComponentLifecycle(StrEnum):
    CREATED = "CREATED"
    IN_PRODUCTION = "IN_PRODUCTION"
    COMPLETED = "COMPLETED"
    SCRAPPED = "SCRAPPED"


class ExecutionState(StrEnum):
    READY = "READY"
    QUEUED = "QUEUED"
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    PROCESSING = "PROCESSING"
    STEP_COMPLETED = "STEP_COMPLETED"


class _StateRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Identity
    revision: Revision


class ProductionOrderState(_StateRecord):
    lifecycle_state: ProductionOrderLifecycle = ProductionOrderLifecycle.CREATED


class LotState(_StateRecord):
    lifecycle_state: LotLifecycle = LotLifecycle.CREATED
    execution_state: ExecutionState = ExecutionState.READY


class SerializedComponentState(_StateRecord):
    lifecycle_state: SerializedComponentLifecycle = SerializedComponentLifecycle.CREATED
    execution_state: ExecutionState = ExecutionState.READY
