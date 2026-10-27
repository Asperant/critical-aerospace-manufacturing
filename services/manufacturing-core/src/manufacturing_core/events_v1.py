"""Core-owned domain-event envelopes for the transactional outbox.

Payload schemas remain producer-owned under ``contracts/v1``.  These models add
the event-envelope fields needed by the Core outbox and reject identity drift
between the envelope and its versioned payload.
"""

from __future__ import annotations

from datetime import UTC
from typing import Annotated, Literal, TypeAlias
from uuid import uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

Identity = Annotated[str, StringConstraints(strict=True, pattern=r"^\S+$")]
NonBlankText = Annotated[
    str, StringConstraints(strict=True, min_length=1, pattern=r".*\S.*")
]
PositiveVersion = Annotated[int, Field(gt=0)]


class EntityReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entity_type: Identity
    id: Identity
    revision: Identity


class UtcOccurrence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    clock: Literal["UTC"]
    value: AwareDatetime


class LotHeldPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: Literal["production.lot-held"]
    schema_version: Literal[1]
    aggregate_type: Literal["Lot"]
    aggregate_id: Identity
    aggregate_version: PositiveVersion
    lot_id: Identity
    lot_revision: Identity
    material_hold_id: Identity
    reason: NonBlankText

    @model_validator(mode="after")
    def identity_matches_aggregate(self) -> LotHeldPayloadV1:
        if self.aggregate_id != self.lot_id:
            raise ValueError("lot_id must equal aggregate_id")
        return self


class LotDispatchAuthorizedPayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_type: Literal["production.lot-dispatch-authorized"]
    schema_version: Literal[1]
    aggregate_type: Literal["Lot"]
    aggregate_id: Identity
    aggregate_version: PositiveVersion
    lot_id: Identity
    lot_revision: Identity
    dispatch_id: Identity

    @model_validator(mode="after")
    def identity_matches_aggregate(self) -> LotDispatchAuthorizedPayloadV1:
        if self.aggregate_id != self.lot_id:
            raise ValueError("lot_id must equal aggregate_id")
        return self


class _CoreEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: Identity
    producer: Literal["manufacturing-core"]
    world_id: Identity
    correlation_id: Identity
    causation_id: Identity | None
    trace_id: Identity
    occurred_at: UtcOccurrence
    observed_at: AwareDatetime
    entity_refs: tuple[EntityReference, ...]

    @model_validator(mode="after")
    def occurred_at_is_utc(self) -> _CoreEvent:
        if self.occurred_at.value.utcoffset() != UTC.utcoffset(self.occurred_at.value):
            raise ValueError("occurred_at must be UTC")
        if self.observed_at.utcoffset() != UTC.utcoffset(self.observed_at):
            raise ValueError("observed_at must be UTC")
        return self


class LotHeldEvent(_CoreEvent):
    event_type: Literal["production.lot-held"]
    schema_version: Literal[1]
    payload: LotHeldPayloadV1

    @model_validator(mode="after")
    def payload_is_bound(self) -> LotHeldEvent:
        if self.entity_refs != (
            EntityReference(
                entity_type="Lot",
                id=self.payload.aggregate_id,
                revision=self.payload.lot_revision,
            ),
        ):
            raise ValueError("entity reference is not bound to payload")
        return self


class LotDispatchAuthorizedEvent(_CoreEvent):
    event_type: Literal["production.lot-dispatch-authorized"]
    schema_version: Literal[1]
    payload: LotDispatchAuthorizedPayloadV1

    @model_validator(mode="after")
    def payload_is_bound(self) -> LotDispatchAuthorizedEvent:
        if self.entity_refs != (
            EntityReference(
                entity_type="Lot",
                id=self.payload.aggregate_id,
                revision=self.payload.lot_revision,
            ),
        ):
            raise ValueError("entity reference is not bound to payload")
        return self


DomainEventV1: TypeAlias = Annotated[
    LotHeldEvent | LotDispatchAuthorizedEvent,
    Field(discriminator="event_type"),
]


def new_event_id() -> str:
    return str(uuid4())


def new_trace_id() -> str:
    return str(uuid4())
