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
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from uuid import UUID

from cap_artifacts import ArtifactStore, S3Client, StoreConfig
from cap_contracts.envelope import (
    EntityReference,
    EnvelopeError,
    EventEnvelope,
    validate_world_scope,
)
from cap_event_consumer.consumer import (
    Consumer,
    DeliveryContext,
    Event,
)
from cap_event_consumer.ledger import Outcome, ProcessedMessageLedger
from cap_observability.health import Check, health_report
from psycopg import Connection
from psycopg.rows import DictRow

from vision_service.outbox import VisionOutbox, publish_pending
from vision_service.pipeline import EVENT_TYPE, inspect
from vision_service.request import InspectionWork, parse_request

LOGGER = logging.getLogger("vision_service.worker")
DEFAULT_INPUT_EVENTS = ("InspectionRequested", "RunInspection")
DEFAULT_INPUT_SUBJECT = "inspection.requested.v1"
DEFAULT_OUTPUT_SUBJECT = "vision.inspection-observation.v1"
CONSUMER_SCOPE = "inspection-observation/live-v1"


class WorkerError(ValueError):
    """An input or binding failed closed without producing an observation."""


class Delivery(Protocol):
    @property
    def data(self) -> bytes: ...

    async def ack(self) -> None: ...

    async def nak(self) -> None: ...


class Publisher(Protocol):
    async def publish(self, subject: str, data: bytes, *, message_id: str) -> Any: ...


@dataclass(frozen=True)
class WorkerConfig:
    """Explicit deployment binding; no stream or subject is inferred at runtime."""

    nats_url: str
    database_dsn: str = field(repr=False)
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
            database_dsn=required("CAP_VISION_DATABASE_URL"),
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
                self.database_dsn,
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
    output_id = uuid.uuid5(
        UUID("cbcad437-04fb-5d6c-9f05-fc5db50fd012"),
        f"vision.inspection-observation.v1:{incoming.event_id}",
    )
    return EventEnvelope(
        event_id=cast(Any, str(output_id)),
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
    """Persist one idempotent local effect before ACK; relay publication separately."""

    def __init__(
        self,
        reader: Any,
        publisher: Publisher,
        config: WorkerConfig,
        *,
        clock: Any,
        connect: Any,
    ) -> None:
        config.validate()
        self.reader = reader
        self.publisher = publisher
        self.config = config
        self.clock = clock
        self.connect = connect
        self.outbox = VisionOutbox()
        self.consumer = Consumer(
            ledger=ProcessedMessageLedger("vision_consumer"),
            scope=CONSUMER_SCOPE,
            connect=connect,
            identify=self._identify,
            admit=self._admit,
            effect=self._effect,
        )

    def _identify(self, data: bytes) -> Event:
        incoming, payload = _decode(data, self.config)
        work = parse_request(payload)
        with self.connect() as connection:
            processed = connection.execute(
                "SELECT 1 FROM vision_consumer.processed_message "
                "WHERE consumer_scope = %s AND event_id = %s",
                (CONSUMER_SCOPE, str(incoming.event_id)),
            ).fetchone()
        if processed is not None:
            return Event(
                str(incoming.event_id),
                {
                    "correlation_id": str(incoming.correlation_id),
                    "source_event_id": str(incoming.event_id),
                },
            )
        event = _output_envelope(incoming, work, now=self.clock())
        observation = inspect(
            work,
            self.reader,
            observation_id=str(event.event_id),
            clock=self.clock,
        )
        output = {"envelope": event.to_mapping(), "payload": observation}
        return Event(
            str(incoming.event_id),
            {
                "correlation_id": str(incoming.correlation_id),
                "source_event_id": str(incoming.event_id),
                "output_event_id": str(event.event_id),
                "subject": self.config.output_subject,
                "output": output,
            },
        )

    def _admit(
        self, _connection: Connection[DictRow], event: Event, context: DeliveryContext
    ) -> None:
        if context.replay:
            raise WorkerError("Vision live effects reject replay context")
        if event.body.get("source_event_id") != event.event_id:
            raise WorkerError("source event identity changed during processing")
        if event.body.get("subject") != self.config.output_subject:
            raise WorkerError("Vision output subject differs from deployment binding")
        raw_output = event.body.get("output")
        if not isinstance(raw_output, Mapping):
            raise WorkerError("inspection observation output is invalid")
        output = cast(Mapping[str, object], raw_output)
        raw_envelope = output.get("envelope")
        raw_observation = output.get("payload")
        event_id = event.body.get("output_event_id")
        if not isinstance(raw_envelope, Mapping) or not isinstance(
            raw_observation, Mapping
        ):
            raise WorkerError("Vision output identity is inconsistent")
        output_envelope = cast(Mapping[str, object], raw_envelope)
        observation = cast(Mapping[str, object], raw_observation)
        if (
            output_envelope.get("event_id") != event_id
            or observation.get("observation_id") != event_id
        ):
            raise WorkerError("Vision output identity is inconsistent")

    def _effect(
        self, connection: Connection[DictRow], event: Event, _context: DeliveryContext
    ) -> None:
        output = event.body["output"]
        if not isinstance(output, Mapping):
            raise WorkerError("inspection observation output is invalid")
        self.outbox.enqueue(
            connection,
            source_event_id=event.event_id,
            event_id=str(event.body["output_event_id"]),
            subject=str(event.body["subject"]),
            payload=cast(Mapping[str, object], output),
        )

    async def handle(self, delivery: Delivery) -> Outcome:
        return await self.consumer.handle(delivery, DeliveryContext())

    async def publish_pending(self, *, limit: int = 25) -> int:
        return await publish_pending(
            self.outbox, self.connect, self.publisher, limit=limit
        )

    def health(
        self,
        *,
        nats_connected: bool,
        artifact_store_ready: bool,
        database_ready: bool,
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
                Check(
                    "postgresql",
                    "dependency",
                    "REQUIRED",
                    "READY" if database_ready else "UNAVAILABLE",
                ),
                Check("worker", "readiness", "REQUIRED", "READY"),
            ],
        )

    def metrics(self) -> dict[str, int]:
        counts = self.consumer.health()["delivery_counts"]
        return cast(dict[str, int], counts)


class _JetStreamPublisher:
    def __init__(self, jetstream: Any) -> None:
        self.jetstream = jetstream

    async def publish(self, subject: str, data: bytes, *, message_id: str) -> Any:
        return await self.jetstream.publish(
            subject, data, headers={"Nats-Msg-Id": message_id}
        )


async def run_nats(config: WorkerConfig, worker: VisionWorker) -> None:
    """Bind an existing JetStream durable and serve until cancelled.

    Stream/durable provisioning remains a runtime-owner operation. The worker
    verifies the stream exists and never creates or edits broker topology.
    """
    subscription: Any | None = None
    try:
        import nats
        from cap_event_consumer.jetstream import Binding, JetStreamConsumer
        from nats.errors import TimeoutError as NatsTimeoutError
        from nats.js.api import DeliverPolicy
    except ImportError as exc:  # pragma: no cover - packaging failure
        raise WorkerError("nats-py is required for the broker worker") from exc
    config.validate()
    nats_module: Any = nats
    connection = await nats_module.connect(config.nats_url)
    try:
        jetstream = connection.jetstream()
        subscription = await JetStreamConsumer.bind(
            jetstream,
            Binding(
                stream=config.input_stream,
                subject=config.input_subject,
                durable=config.input_durable,
                ack_wait=config.ack_wait_seconds,
                max_deliver=config.max_deliver,
                deliver_policy=DeliverPolicy.ALL,
            ),
            worker.consumer,
            DeliveryContext(),
            ack_timeout=config.ack_wait_seconds,
        )
        worker.publisher = _JetStreamPublisher(jetstream)
        while True:
            try:
                await worker.publish_pending()
            except Exception:
                LOGGER.warning("Vision outbox publication failed; it remains retryable")
            try:
                await subscription.receive_once(timeout=5)
            except (NatsTimeoutError, TimeoutError):
                continue
    finally:
        if subscription is not None:
            await subscription.close()
        await connection.close()


def artifact_store_from_env() -> ArtifactStore:
    """Build the production reader using the approved SeaweedFS S3 boundary."""
    client = S3Client(StoreConfig.from_env(role="reader"))
    return ArtifactStore(client)
