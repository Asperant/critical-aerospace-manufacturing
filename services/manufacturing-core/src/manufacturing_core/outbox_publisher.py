"""NATS JetStream transport binding for validated Core outbox events.

Core persists event intent before this adapter publishes it. The event id is
also used as JetStream's deduplication key; the downstream ledger remains the
durable idempotency boundary when a retry arrives outside JetStream's window.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from cap_contracts.envelope import EnvelopeError, EventEnvelope

from .observability import record_outbox_publication_delay
from .outbox import OutboxRecord


class JetStreamPublishContext(Protocol):
    async def publish(
        self,
        subject: str,
        payload: bytes,
        *,
        timeout: float | None = None,
        stream: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any: ...


class OutboxPublicationError(RuntimeError):
    """A persisted outbox event was not acknowledged by its bound stream."""


@dataclass(frozen=True)
class JetStreamOutboxPublisher:
    jetstream: JetStreamPublishContext
    stream: str
    subject: str

    def __post_init__(self) -> None:
        if not self.stream.strip() or not self.subject.strip():
            raise ValueError("explicit nonblank stream and subject are required")

    async def publish(self, record: OutboxRecord) -> Any:
        """Publish one typed event and return only after its stream ACK."""
        event = record.event.model_dump(mode="json")
        payload = event.pop("payload")
        try:
            envelope = EventEnvelope.from_mapping(event)
        except (EnvelopeError, TypeError, ValueError) as exc:
            raise OutboxPublicationError("Core event envelope rejected") from exc

        wire = json.dumps(
            {"envelope": envelope.to_mapping(), "payload": payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            acknowledgement = await self.jetstream.publish(
                self.subject,
                wire,
                stream=self.stream,
                headers={"Nats-Msg-Id": envelope.event_id},
            )
        except Exception as exc:
            raise OutboxPublicationError(
                "JetStream publication was not acknowledged"
            ) from exc
        if getattr(acknowledgement, "stream", None) != self.stream:
            raise OutboxPublicationError("JetStream ACK came from an unexpected stream")
        record_outbox_publication_delay(record.created_at)
        return acknowledgement
