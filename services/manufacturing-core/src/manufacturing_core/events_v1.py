"""WP-CORE-005 initial Core fact contracts; validation grants no authority."""

from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    model_validator,
)

from manufacturing_core.domain import Identity, Revision


class PayloadV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LotReleasedPayloadV1(PayloadV1):
    lot_id: Identity


class MaterialHoldAppliedPayloadV1(PayloadV1):
    material_hold_id: Identity


class QualityExcursionConfirmedPayloadV1(PayloadV1):
    quality_excursion_id: Identity


class ScheduleActivatedPayloadV1(PayloadV1):
    schedule_id: Identity


class CoreEventV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: Identity
    schema_version: Literal["1"]
    producer: Literal["manufacturing-core"]
    source: Identity
    world_id: Identity
    simulation_run_id: Identity
    branch_id: Identity
    occurred_at: AwareDatetime = Field(
        json_schema_extra={"pattern": r"T.*(?:Z|[+-][0-9]{2}:[0-9]{2})$"}
    )
    aggregate_id: Identity
    aggregate_version: Revision
    correlation_id: Identity
    causation_id: Identity
    trace_id: Identity


class LotReleasedV1(CoreEventV1):
    event_type: Literal["production.LotReleased"]
    aggregate_type: Literal["Lot"]
    payload: LotReleasedPayloadV1


class MaterialHoldAppliedV1(CoreEventV1):
    event_type: Literal["production.MaterialHoldApplied"]
    aggregate_type: Literal["MaterialHold"]
    payload: MaterialHoldAppliedPayloadV1


class QualityExcursionConfirmedV1(CoreEventV1):
    event_type: Literal["quality.QualityExcursionConfirmed"]
    aggregate_type: Literal["QualityExcursion"]
    payload: QualityExcursionConfirmedPayloadV1


class ScheduleActivatedV1(CoreEventV1):
    event_type: Literal["scheduling.ScheduleActivated"]
    aggregate_type: Literal["ScheduleVersion"]
    payload: ScheduleActivatedPayloadV1


class DomainEventV1(
    RootModel[
        Annotated[
            LotReleasedV1
            | MaterialHoldAppliedV1
            | QualityExcursionConfirmedV1
            | ScheduleActivatedV1,
            Field(discriminator="event_type"),
        ]
    ]
):
    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:cap:core:domain-event:v1",
        },
    )

    @model_validator(mode="after")
    def bound_identity(self) -> Self:
        payload = self.root.payload
        if isinstance(payload, LotReleasedPayloadV1):
            identity = payload.lot_id
        elif isinstance(payload, MaterialHoldAppliedPayloadV1):
            identity = payload.material_hold_id
        elif isinstance(payload, QualityExcursionConfirmedPayloadV1):
            identity = payload.quality_excursion_id
        else:
            identity = payload.schedule_id
        if self.root.aggregate_id != identity:
            raise ValueError("payload identity must equal aggregate_id")
        return self
