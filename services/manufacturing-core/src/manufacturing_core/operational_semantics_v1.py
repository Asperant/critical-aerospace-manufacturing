"""Transport-free Core lot operational-semantics contract v1 (read-only view).

Publishes, for one lot, the three independent state dimensions the Simulator
must honour: lifecycle and execution state, the retained material-hold history,
and the append-only component execution/rework history. It reuses the merged
WP-CORE-001/002/004 values; it introduces no transition, rework execution or
persistence behaviour and grants no authority.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Final, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    StringConstraints,
    model_validator,
)

from manufacturing_core.domain import Entity, Identity
from manufacturing_core.lifecycle import ExecutionState, LotLifecycle
from manufacturing_core.rework import ComponentExecutionHistory

CONTRACT_VERSION: Final = "core.lot-operational-semantics.v1"


class HoldStatusV1(StrEnum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class LotOperationalStateV1(Entity):
    """Lot identity and revision with independent lifecycle and execution state."""

    order_id: Identity
    lifecycle_state: LotLifecycle
    execution_state: ExecutionState


class MaterialHoldRecordV1(BaseModel):
    """A retained hold; RELEASED rows are history, not deletion tombstones."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: Identity
    lot_id: Identity
    reason: Annotated[str, StringConstraints(strict=True, pattern=r"\S")]
    status: HoldStatusV1
    placed_at: AwareDatetime
    released_at: AwareDatetime | None = None
    release_reason: (
        Annotated[str, StringConstraints(strict=True, pattern=r"\S")] | None
    ) = None

    @model_validator(mode="after")
    def status_fields(self) -> Self:
        released = (self.released_at, self.release_reason)
        if self.status is HoldStatusV1.ACTIVE and any(v is not None for v in released):
            raise ValueError("an active hold has no release fields")
        if self.status is HoldStatusV1.RELEASED:
            if self.released_at is None or self.release_reason is None:
                raise ValueError("a released hold needs release time and reason")
            if self.released_at < self.placed_at:
                raise ValueError("hold release precedes placement")
        return self


class LotOperationalSemanticsV1(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:cap:core:lot-operational-semantics:v1",
        },
    )

    contract_version: Literal["core.lot-operational-semantics.v1"]
    lot: LotOperationalStateV1
    holds: tuple[MaterialHoldRecordV1, ...]
    component_histories: tuple[ComponentExecutionHistory, ...]

    @model_validator(mode="after")
    def consistent_view(self) -> Self:
        if any(hold.lot_id != self.lot.id for hold in self.holds):
            raise ValueError("hold references a different lot")
        if len({hold.id for hold in self.holds}) != len(self.holds):
            raise ValueError("duplicate hold identity")
        if sum(h.status is HoldStatusV1.ACTIVE for h in self.holds) > 1:
            raise ValueError("at most one active hold per lot")
        order = [(hold.placed_at, hold.id) for hold in self.holds]
        if order != sorted(order):
            raise ValueError("holds must be ordered by placement time then identity")
        components = [history.component_id for history in self.component_histories]
        if len(set(components)) != len(components):
            raise ValueError("duplicate component history")
        if components != sorted(components):
            raise ValueError("component histories must be ordered by identity")
        return self
