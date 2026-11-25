from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import manufacturing_core.observability as observability_module
import manufacturing_core.outbox_publisher as publisher_module
import pytest
from cap_contracts.envelope import EventEnvelope
from manufacturing_core.events_v1 import EntityReference, UtcOccurrence
from manufacturing_core.events_v2 import LotHeldEventV2, LotHeldPayloadV2
from manufacturing_core.outbox import OutboxRecord
from manufacturing_core.outbox_publisher import (
    JetStreamOutboxPublisher,
    OutboxPublicationError,
)


@dataclass(frozen=True)
class Ack:
    stream: str
    seq: int = 1


class FakeJetStream:
    def __init__(self, ack_stream: str = "CAP_EVENTS") -> None:
        self.ack_stream = ack_stream
        self.call: dict[str, Any] | None = None

    async def publish(
        self,
        subject: str,
        payload: bytes,
        *,
        timeout: float | None = None,
        stream: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Ack:
        self.call = {
            "subject": subject,
            "payload": payload,
            "timeout": timeout,
            "stream": stream,
            "headers": headers,
        }
        return Ack(self.ack_stream)


def record() -> OutboxRecord:
    occurred = datetime(2026, 11, 23, 12, tzinfo=UTC)
    payload = LotHeldPayloadV2(
        event_type="production.lot-held",
        schema_version=2,
        aggregate_type="Lot",
        aggregate_id="LOT-1",
        aggregate_version=1,
        lot_id="LOT-1",
        lot_revision="rev-1",
        material_hold_id="HOLD-1",
        reason="NDT anomaly",
    )
    event = LotHeldEventV2(
        event_id="evt-1",
        producer="manufacturing-core",
        world_id="WORLD-1",
        correlation_id="corr-1",
        causation_id="cmd-1",
        trace_id="trace-1",
        occurred_at=UtcOccurrence(clock="UTC", value=occurred),
        observed_at=occurred,
        entity_refs=(EntityReference(entity_type="Lot", id="LOT-1", revision="rev-1"),),
        event_type="production.lot-held",
        schema_version=2,
        payload=payload,
    )
    return OutboxRecord.new(event, created_at=occurred)


def test_publisher_emits_evt002_envelope_and_jetstream_dedup_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    js = FakeJetStream()
    publisher = JetStreamOutboxPublisher(js, "CAP_EVENTS", "cap.core.events")
    recorded: list[datetime] = []
    monkeypatch.setattr(
        publisher_module, "record_outbox_publication_delay", recorded.append
    )
    outbox = record()

    asyncio.run(publisher.publish(outbox))

    assert js.call is not None
    assert js.call["subject"] == "cap.core.events"
    assert js.call["stream"] == "CAP_EVENTS"
    assert js.call["headers"] == {"Nats-Msg-Id": "evt-1"}
    wire = json.loads(js.call["payload"])
    envelope = EventEnvelope.from_mapping(wire["envelope"])
    assert envelope.event_id == "evt-1"
    assert envelope.world_id == "WORLD-1"
    assert envelope.event_type == "production.lot-held"
    assert wire["payload"]["schema_version"] == 2
    assert wire["payload"]["aggregate_version"] == 1
    assert recorded == [outbox.created_at]


def test_publisher_rejects_ack_from_wrong_stream() -> None:
    publisher = JetStreamOutboxPublisher(
        FakeJetStream("OTHER_STREAM"), "CAP_EVENTS", "cap.core.events"
    )

    with pytest.raises(OutboxPublicationError, match="unexpected stream"):
        asyncio.run(publisher.publish(record()))


def test_outbox_publication_delay_records_seconds_without_event_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from manufacturing_core.observability import record_outbox_publication_delay

    class Histogram:
        def __init__(self) -> None:
            self.name: str | None = None
            self.unit: str | None = None
            self.description: str | None = None
            self.values: list[float] = []

        def create_histogram(
            self, name: str, *, unit: str, description: str
        ) -> Histogram:
            self.name = name
            self.unit = unit
            self.description = description
            return self

        def record(self, value: float) -> None:
            self.values.append(value)

    histogram = Histogram()
    monkeypatch.setattr(observability_module, "_OUTBOX_PUBLICATION_DELAY", None)
    monkeypatch.setattr("opentelemetry.metrics.get_meter", lambda service: histogram)
    created = datetime(2026, 11, 25, 12, tzinfo=UTC)
    record_outbox_publication_delay(
        created, published_at=datetime(2026, 11, 25, 12, 0, 1, 250000, tzinfo=UTC)
    )

    assert histogram.name == "core.outbox.publication_delay"
    assert histogram.unit == "s"
    assert "durable broker acknowledgement" in str(histogram.description)
    assert histogram.values == [1.25]


def test_outbox_publication_delay_rejects_naive_timestamps() -> None:
    from manufacturing_core.observability import record_outbox_publication_delay

    with pytest.raises(ValueError, match="timezone-aware"):
        record_outbox_publication_delay(datetime(2026, 11, 25, 12))


@pytest.mark.parametrize(("stream", "subject"), [("", "events"), ("stream", " ")])
def test_publisher_requires_explicit_binding(stream: str, subject: str) -> None:
    with pytest.raises(ValueError, match="explicit nonblank"):
        JetStreamOutboxPublisher(FakeJetStream(), stream, subject)
