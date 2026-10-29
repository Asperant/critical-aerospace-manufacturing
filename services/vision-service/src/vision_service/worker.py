"""Fail-closed Vision request worker and JetStream binding.

The worker consumes the canonical asynchronous ``InspectionRequested`` or
``RunInspection`` envelope, reads the referenced artifact through the real
``ArtifactStore`` boundary, and publishes one immutable
``InspectionObservation`` event.  It never mutates Core state and never treats
an inspection failure as a no-defect result.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from cap_artifacts import ArtifactStore, S3Client, StoreConfig
from cap_contracts.envelope import (
    EntityReference,
    EnvelopeError,
    EventEnvelope,
    validate_world_scope,
)
from cap_observability.health import Check, health_report

from vision_service.pipeline import EVENT_TYPE, inspect
from vision_service.request import InspectionWork, RequestError, parse_request

LOGGER = logging.getLogger("vision_service.worker")
DEFAULT_INPUT_EVENTS = ("InspectionRequested", "RunInspection")
DEFAULT_INPUT_SUBJECT = "inspection.requested.v1"
DEFAULT_OUTPUT_SUBJECT = "vision.inspection-observation.v1"


class WorkerError(ValueError):
    """An input or binding failed closed without producing an observation."""


class Delivery(Protocol):
    @property
    def data(self) -> bytes: ...

    async def ack(self) -> None: ...

    async def nak(self) -> None: ...


class Publisher(Protocol):
    async def publish(self, subject: str, data: bytes) -> Any: ...


@dataclass(frozen=True)
class WorkerConfig:
    """Explicit deployment binding; no stream or subject is inferred at runtime."""

    nats_url: str
    input_stream: str
    input_subject: str
    input_durable: str
    output_subject: str
    world_id: str
    input_event_types: tuple[str, ...] = DEFAULT_INPUT_EVENTS
    allowed_producers: tuple[str, ...] = (
        "manufacturing-core",
        "manufacturing-simulator",
    )
    ack_wait_seconds: float = 30.0
    max_deliver: int = 5

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> WorkerConfig:
        values = os.environ if env is None else env

        def required(name: str) -> str:
            value = values.get(name, "").strip()
            if not value:
                raise WorkerError(f"{name} is required")
            return value

        raw_events = values.get("CAP_VISION_INPUT_EVENT_TYPES", "")
        events = (
            tuple(item.strip() for item in raw_events.split(",") if item.strip())
            or DEFAULT_INPUT_EVENTS
        )
        if len(set(events)) != len(events):
            raise WorkerError("CAP_VISION_INPUT_EVENT_TYPES must be unique")
        return cls(
            nats_url=required("CAP_NATS_URL"),
            input_stream=required("CAP_VISION_INPUT_STREAM"),
            input_subject=values.get("CAP_VISION_INPUT_SUBJECT", DEFAULT_INPUT_SUBJECT),
            input_durable=required("CAP_VISION_INPUT_DURABLE"),
            output_subject=values.get(
                "CAP_VISION_OUTPUT_SUBJECT", DEFAULT_OUTPUT_SUBJECT
            ),
            world_id=required("CAP_VISION_WORLD_ID"),
            input_event_types=events,
            ack_wait_seconds=float(values.get("CAP_VISION_ACK_WAIT_SECONDS", "30")),
            max_deliver=int(values.get("CAP_VISION_MAX_DELIVER", "5")),
        )

    def validate(self) -> None:
        if not all(
            value.strip()
            for value in (
                self.nats_url,
                self.input_stream,
                self.input_subject,
                self.input_durable,
                self.output_subject,
                self.world_id,
            )
        ):
            raise WorkerError("NATS binding values must be nonblank")
        if not self.input_event_types or not self.allowed_producers:
            raise WorkerError("input event and producer allowlists must be nonempty")
        if self.ack_wait_seconds <= 0 or self.max_deliver < 1:
            raise WorkerError("ack wait and max deliver must be positive")


def _decode(
    data: bytes, config: WorkerConfig
) -> tuple[EventEnvelope, Mapping[str, object]]:
    try:
        value = json.loads(data)
    except (TypeError, ValueError):
        raise WorkerError("event: invalid JSON") from None
    if not isinstance(value, Mapping):
        raise WorkerError("event: object required")
    mapping = cast(Mapping[str, object], value)
    if set(mapping) != {"envelope", "payload"}:
        raise WorkerError("event: envelope and payload are required")
    raw_envelope = mapping["envelope"]
    raw_payload = mapping["payload"]
    try:
        envelope = EventEnvelope.from_mapping(raw_envelope)
        validate_world_scope(envelope, config.world_id)
    except (EnvelopeError, ValueError):
        raise WorkerError("event: invalid envelope or world scope") from None
    if envelope.event_type not in config.input_event_types:
        raise WorkerError("event_type: unsupported Vision input")
    if envelope.producer not in config.allowed_producers:
        raise WorkerError("producer: not allowed for Vision input")
    if not isinstance(raw_payload, Mapping):
        raise WorkerError("payload: object required")
    payload = dict(cast(Mapping[str, object], raw_payload))
    declared_type = payload.get("event_type")
    if declared_type is not None and declared_type != envelope.event_type:
        raise WorkerError("event_type: envelope/payload mismatch")
    return envelope, payload


def _output_envelope(
    incoming: EventEnvelope, work: InspectionWork, *, now: datetime
) -> EventEnvelope:
    observed = now.astimezone(UTC)
    return EventEnvelope(
        event_id=cast(Any, str(uuid.uuid4())),
        event_type=EVENT_TYPE,
        schema_version=1,
        producer="vision-service",
        world_id=work.world_id,
        correlation_id=incoming.correlation_id,
        causation_id=cast(Any, incoming.event_id),
        trace_id=incoming.trace_id,
        occurred_at=observed,
        observed_at=observed,
        entity_refs=(
            EntityReference(
                "SerializedComponent",
                cast(Any, work.subject.serialized_component_id),
                cast(Any, work.subject.serialized_component_revision),
            ),
        ),
    )


class VisionWorker:
    """Process one delivery and ACK only after observation publication."""

    def __init__(
        self,
        reader: Any,
        publisher: Publisher,
        config: WorkerConfig,
        *,
        clock: Any,
    ) -> None:
        config.validate()
        self.reader = reader
        self.publisher = publisher
        self.config = config
        self.clock = clock
        self._counts: dict[str, int] = {}

    async def handle(self, delivery: Delivery) -> dict[str, Any]:
        try:
            incoming, payload = _decode(delivery.data, self.config)
            work = parse_request(payload)
            observation = inspect(
                work,
                self.reader,
                observation_id=str(uuid.uuid4()),
                clock=self.clock,
            )
            event = _output_envelope(incoming, work, now=self.clock())
            body = json.dumps(
                {"envelope": event.to_mapping(), "payload": observation},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            await self.publisher.publish(self.config.output_subject, body)
            await delivery.ack()
            self._counts["processed"] = self._counts.get("processed", 0) + 1
            LOGGER.info(
                "inspection observation published",
                extra={
                    "event_id": event.event_id,
                    "correlation_id": incoming.correlation_id,
                    "inspection_request_id": work.inspection_request_id,
                    "outcome": observation["outcome"],
                },
            )
            return observation
        except (WorkerError, RequestError, EnvelopeError, ValueError, OSError):
            self._counts["failed"] = self._counts.get("failed", 0) + 1
            LOGGER.warning("inspection delivery rejected or failed", exc_info=True)
            await delivery.nak()
            raise
        except Exception:
            self._counts["failed"] = self._counts.get("failed", 0) + 1
            LOGGER.exception("inspection delivery failed unexpectedly")
            await delivery.nak()
            raise

    def health(
        self, *, nats_connected: bool, artifact_store_ready: bool
    ) -> dict[str, Any]:
        return health_report(
            "vision-service",
            "runtime",
            [
                Check(
                    "nats-jetstream",
                    "dependency",
                    "REQUIRED",
                    "READY" if nats_connected else "UNAVAILABLE",
                ),
                Check(
                    "artifact-store",
                    "dependency",
                    "REQUIRED",
                    "READY" if artifact_store_ready else "UNAVAILABLE",
                ),
                Check("worker", "readiness", "REQUIRED", "READY"),
            ],
        )

    def metrics(self) -> dict[str, int]:
        return dict(self._counts)


class _NatsDelivery:
    def __init__(self, message: Any) -> None:
        self.message = message

    @property
    def data(self) -> bytes:
        return self.message.data

    async def ack(self) -> None:
        await self.message.ack()

    async def nak(self) -> None:
        await self.message.nak()


class _JetStreamPublisher:
    def __init__(self, jetstream: Any) -> None:
        self.jetstream = jetstream

    async def publish(self, subject: str, data: bytes) -> Any:
        return await self.jetstream.publish(subject, data)


async def run_nats(config: WorkerConfig, worker: VisionWorker) -> None:
    """Bind an existing JetStream durable and serve until cancelled.

    Stream/durable provisioning remains a runtime-owner operation. The worker
    verifies the stream exists and never creates or edits broker topology.
    """
    try:
        import nats
        from nats.js.api import AckPolicy, ConsumerConfig, DeliverPolicy
    except ImportError as exc:  # pragma: no cover - packaging failure
        raise WorkerError("nats-py is required for the broker worker") from exc
    config.validate()
    nats_module: Any = nats
    connection = await nats_module.connect(config.nats_url)
    try:
        jetstream = connection.jetstream()
        await jetstream.stream_info(config.input_stream)
        consumer = ConsumerConfig(
            durable_name=config.input_durable,
            filter_subject=config.input_subject,
            ack_policy=AckPolicy.EXPLICIT,
            ack_wait=config.ack_wait_seconds,
            max_deliver=config.max_deliver,
            deliver_policy=DeliverPolicy.ALL,
        )
        subscription = await jetstream.pull_subscribe(
            config.input_subject,
            durable=config.input_durable,
            stream=config.input_stream,
            config=consumer,
        )
        worker.publisher = _JetStreamPublisher(jetstream)
        while True:
            messages = await subscription.fetch(batch=1, timeout=5)
            await worker.handle(_NatsDelivery(messages[0]))
    finally:
        await connection.close()


def artifact_store_from_env() -> ArtifactStore:
    """Build the production reader using the approved SeaweedFS S3 boundary."""
    client = S3Client(StoreConfig.from_env(role="reader"))
    return ArtifactStore(client)
