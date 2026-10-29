from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import pytest
from cap_contracts.envelope import (
    CausationID,
    CorrelationID,
    EntityID,
    EntityReference,
    EntityRevision,
    EventEnvelope,
    EventID,
    TraceID,
)
from conftest import encode_png, gray, reference_for, request_for, store_with, textured
from vision_service import VisionWorker, WorkerConfig, WorkerError


class Delivery:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.acked = 0
        self.naked = 0

    async def ack(self) -> None:
        self.acked += 1

    async def nak(self) -> None:
        self.naked += 1


class Publisher:
    def __init__(self, *, fail: bool = False) -> None:
        self.messages: list[tuple[str, bytes]] = []
        self.fail = fail

    async def publish(self, subject: str, data: bytes) -> None:
        if self.fail:
            raise OSError("broker unavailable")
        self.messages.append((subject, data))


def config() -> WorkerConfig:
    return WorkerConfig(
        nats_url="nats://localhost:4222",
        input_stream="CAP_EVENTS",
        input_subject="inspection.requested.v1",
        input_durable="vision-service",
        output_subject="vision.inspection-observation.v1",
        world_id="world-production",
    )


def envelope() -> EventEnvelope:
    return EventEnvelope(
        event_id=EventID("evt-request-1"),
        event_type="InspectionRequested",
        schema_version=1,
        producer="manufacturing-core",
        world_id="world-production",
        correlation_id=CorrelationID("corr-1"),
        causation_id=CausationID("evt-root"),
        trace_id=TraceID("trace-1"),
        occurred_at=datetime(2026, 10, 29, tzinfo=UTC),
        observed_at=datetime(2026, 10, 29, tzinfo=UTC),
        entity_refs=(
            EntityReference(
                "SerializedComponent", EntityID("C-1"), EntityRevision("r1")
            ),
        ),
    )


def message(request: dict[str, Any], event: EventEnvelope | None = None) -> bytes:
    return json.dumps(
        {"envelope": (event or envelope()).to_mapping(), "payload": request}
    ).encode()


def worker(publisher: Publisher, store: Any) -> VisionWorker:
    now = iter(datetime(2026, 10, 29, 10, 0, n, tzinfo=UTC) for n in range(10))
    return VisionWorker(store, publisher, config(), clock=lambda: next(now))


def request_and_store() -> tuple[dict[str, Any], Any]:
    image = encode_png(gray(textured(seed=3)))
    ref = reference_for(
        image,
        **{
            "context": {
                "world_id": "world-production",
                "simulation_run_id": None,
                "branch_id": None,
            }
        },
    )
    return request_for(ref, world_id="world-production"), store_with(ref, image)


def test_worker_publishes_observation_before_ack() -> None:
    request, store = request_and_store()
    publisher = Publisher()
    delivery = Delivery(message(request))
    observation = asyncio.run(worker(publisher, store).handle(delivery))

    assert observation["event_type"] == "vision.inspection-observation"
    assert delivery.acked == 1 and delivery.naked == 0
    assert len(publisher.messages) == 1
    subject, body = publisher.messages[0]
    assert subject == config().output_subject
    event = json.loads(body)
    assert event["envelope"]["causation_id"] == "evt-request-1"
    assert event["envelope"]["correlation_id"] == "corr-1"
    assert event["payload"] == observation


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(unexpected=True),
        lambda value: value.pop("artifact"),
    ],
)
def test_malformed_request_is_naked_without_publication(mutate: Any) -> None:
    request, store = request_and_store()
    mutate(request)
    publisher = Publisher()
    delivery = Delivery(message(request))
    with pytest.raises((WorkerError, ValueError)):
        asyncio.run(worker(publisher, store).handle(delivery))
    assert delivery.acked == 0 and delivery.naked == 1 and not publisher.messages


def test_wrong_scope_or_oracle_artifact_is_naked() -> None:
    request, store = request_and_store()
    request["artifact"]["classification"] = "RESTRICTED_ORACLE"
    publisher = Publisher()
    delivery = Delivery(message(request))
    with pytest.raises(ValueError):
        asyncio.run(worker(publisher, store).handle(delivery))
    assert delivery.naked == 1 and not publisher.messages


def test_publication_failure_is_naked_and_not_acked() -> None:
    request, store = request_and_store()
    publisher = Publisher(fail=True)
    delivery = Delivery(message(request))
    with pytest.raises(OSError):
        asyncio.run(worker(publisher, store).handle(delivery))
    assert delivery.acked == 0 and delivery.naked == 1


def test_health_is_dependency_aware() -> None:
    report = worker(Publisher(), object()).health(
        nats_connected=False, artifact_store_ready=True
    )
    assert report["status"] == "UNAVAILABLE"
    assert report["service"] == "vision-service"
