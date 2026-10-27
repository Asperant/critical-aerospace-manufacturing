"""Core outbox event envelope and payload identity tests."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from manufacturing_core.events_v1 import (
    EntityReference,
    LotDispatchAuthorizedEvent,
    LotDispatchAuthorizedPayloadV1,
    LotHeldEvent,
    LotHeldPayloadV1,
    UtcOccurrence,
)
from pydantic import ValidationError


def held_payload(**overrides: object) -> LotHeldPayloadV1:
    values: dict[str, object] = {
        "event_type": "production.lot-held",
        "schema_version": 1,
        "aggregate_type": "Lot",
        "aggregate_id": "LOT-1",
        "aggregate_version": 1,
        "lot_id": "LOT-1",
        "lot_revision": "rev-1",
        "material_hold_id": "HOLD-1",
        "reason": "inspection-anomaly",
    }
    values.update(overrides)
    return LotHeldPayloadV1.model_validate(values)


def test_lot_held_event_round_trip_preserves_envelope_and_payload() -> None:
    payload = held_payload()
    event = LotHeldEvent(
        event_id="event-1",
        producer="manufacturing-core",
        world_id="primary",
        correlation_id="corr-1",
        causation_id="command-1",
        trace_id="trace-1",
        occurred_at=UtcOccurrence(
            clock="UTC", value=datetime(2026, 10, 27, 12, tzinfo=UTC)
        ),
        observed_at=datetime(2026, 10, 27, 12, tzinfo=UTC),
        entity_refs=(EntityReference(entity_type="Lot", id="LOT-1", revision="rev-1"),),
        event_type="production.lot-held",
        schema_version=1,
        payload=payload,
    )
    assert LotHeldEvent.model_validate(event.model_dump()) == event


def test_payload_identity_and_event_identity_must_match() -> None:
    with pytest.raises(ValidationError, match="lot_id must equal aggregate_id"):
        held_payload(lot_id="LOT-OTHER")
    payload = held_payload()
    with pytest.raises(ValidationError, match="entity reference is not bound"):
        LotHeldEvent(
            event_id="event-1",
            producer="manufacturing-core",
            world_id="primary",
            correlation_id="corr-1",
            causation_id=None,
            trace_id="trace-1",
            occurred_at=UtcOccurrence(
                clock="UTC", value=datetime(2026, 10, 27, 12, tzinfo=UTC)
            ),
            observed_at=datetime(2026, 10, 27, 12, tzinfo=UTC),
            entity_refs=(
                EntityReference(entity_type="Lot", id="LOT-OTHER", revision="rev-1"),
            ),
            event_type="production.lot-held",
            schema_version=1,
            payload=payload,
        )


def test_lot_held_reason_preserves_nonblank_human_text() -> None:
    assert held_payload(reason="inspection anomaly").reason == "inspection anomaly"
    with pytest.raises(ValidationError):
        held_payload(reason="   ")


def test_dispatch_event_rejects_non_utc_occurrence() -> None:
    payload = LotDispatchAuthorizedPayloadV1(
        event_type="production.lot-dispatch-authorized",
        schema_version=1,
        aggregate_type="Lot",
        aggregate_id="LOT-1",
        aggregate_version=1,
        lot_id="LOT-1",
        lot_revision="rev-2",
        dispatch_id="DISPATCH-1",
    )
    with pytest.raises(ValidationError, match="occurred_at must be UTC"):
        LotDispatchAuthorizedEvent(
            event_id="event-2",
            producer="manufacturing-core",
            world_id="primary",
            correlation_id="corr-1",
            causation_id="command-2",
            trace_id="trace-2",
            occurred_at=UtcOccurrence(
                clock="UTC",
                value=datetime(2026, 10, 27, 12, tzinfo=timezone(timedelta(hours=3))),
            ),
            observed_at=datetime(2026, 10, 27, 12, tzinfo=UTC),
            entity_refs=(
                EntityReference(entity_type="Lot", id="LOT-1", revision="rev-2"),
            ),
            event_type="production.lot-dispatch-authorized",
            schema_version=1,
            payload=payload,
        )
