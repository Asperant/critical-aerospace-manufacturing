"""Versioned Core LotHeld.v2 event payload and envelope.

LotHeld.v1 remains in :mod:`manufacturing_core.events_v1` unchanged.  This
module changes only the reason field contract and carries the explicit schema
version needed by producer and consumer version negotiation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from manufacturing_core.events_v1 import (
    EntityReference,
    _CoreEvent,
)

HumanReason = Annotated[str, StringConstraints(strict=True, min_length=1)]
Identity = Annotated[str, StringConstraints(strict=True, pattern=r"^\S+$")]
PositiveVersion = Annotated[int, Field(gt=0)]


class LotHeldPayloadV2(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: Literal["production.lot-held"]
    schema_version: Literal[2]
    aggregate_type: Literal["Lot"]
    aggregate_id: Identity
    aggregate_version: PositiveVersion
    lot_id: Identity
    lot_revision: Identity
    material_hold_id: Identity
    reason: HumanReason

    @model_validator(mode="after")
    def identity_matches_aggregate(self) -> LotHeldPayloadV2:
        if self.aggregate_id != self.lot_id:
            raise ValueError("lot_id must equal aggregate_id")
        return self


class LotHeldEventV2(_CoreEvent):
    event_type: Literal["production.lot-held"]
    schema_version: Literal[2]
    payload: LotHeldPayloadV2

    @model_validator(mode="after")
    def payload_is_bound(self) -> LotHeldEventV2:
        if self.entity_refs != (
            EntityReference(
                entity_type="Lot",
                id=self.payload.aggregate_id,
                revision=self.payload.lot_revision,
            ),
        ):
            raise ValueError("entity reference is not bound to payload")
        return self
