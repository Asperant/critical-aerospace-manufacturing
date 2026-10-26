"""Application adapter boundary for EVT-002/EVT-003.

Transport binding values are supplied by deployment configuration. This module
does not provision streams or infer a world from message payloads.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from .projector import AdmissionError, ProjectionEvent, Projector


def decode_projection_event(
    data: bytes, *, expected_world_id: str, expected_branch_id: str = "PRIMARY"
) -> ProjectionEvent:
    try:
        value = json.loads(data)
    except (TypeError, ValueError):
        raise AdmissionError("event: invalid JSON") from None
    if not isinstance(value, Mapping):
        raise AdmissionError("event: object required")
    envelope = value.get("envelope", value)
    payload = value.get("payload")
    if not isinstance(envelope, Mapping) or not isinstance(payload, Mapping):
        raise AdmissionError("event: EVT-002 envelope and payload required")
    try:
        from cap_contracts.envelope import EventEnvelope, validate_world_scope

        typed_envelope = EventEnvelope.from_mapping(envelope)
        validate_world_scope(typed_envelope, expected_world_id)
    except ImportError as exc:
        raise AdmissionError("EVT-002 envelope primitive unavailable") from exc
    except ValueError as exc:
        message = (
            "world_id: scope mismatch"
            if "world_id" in str(exc)
            else "EVT-002 envelope rejected"
        )
        raise AdmissionError(message) from exc
    if envelope.get("world_id") != expected_world_id:
        raise AdmissionError("world_id: scope mismatch")
    event_type = envelope.get("event_type")
    if payload.get("event_type") != event_type:
        raise AdmissionError("event_type: envelope/payload mismatch")
    refs = envelope.get("entity_refs")
    if not isinstance(refs, list) or len(refs) != 1 or not isinstance(refs[0], Mapping):
        raise AdmissionError("entity_refs: exactly one aggregate reference required")
    ref = refs[0]
    return ProjectionEvent.from_mapping(
        {
            "event_id": envelope.get("event_id"),
            "event_type": event_type,
            "world_id": envelope.get("world_id"),
            "aggregate_type": payload.get("aggregate_type"),
            "aggregate_id": payload.get("aggregate_id"),
            "aggregate_version": payload.get("aggregate_version", ref.get("revision")),
            "payload": payload,
            "branch_id": envelope.get("branch_id", expected_branch_id),
        }
    )


def apply_delivery(
    projector: Projector,
    data: bytes,
    *,
    expected_world_id: str,
    expected_branch_id: str = "PRIMARY",
):
    """Decode/admit/apply one local effect; caller owns transaction + ACK."""
    event = decode_projection_event(
        data, expected_world_id=expected_world_id, expected_branch_id=expected_branch_id
    )
    return projector.apply(event)


def build_consumer(
    *,
    ledger: Any,
    scope: str,
    connect: Any,
    projector: Projector,
    expected_world_id: str,
):
    """Build the EVT-003 transaction-owning boundary around local projection.

    The application supplies the database connection and JetStream binding. The
    generic consumer owns transaction/ledger/ACK sequencing; this adapter owns
    world admission and the local projector effect.
    """
    try:
        from cap_event_consumer.consumer import AdmissionError as ConsumerAdmissionError
        from cap_event_consumer.consumer import Consumer, DeliveryContext, Event
    except ImportError as exc:
        raise RuntimeError("EVT-003 consumer primitive unavailable") from exc

    def identify(data: bytes) -> Event:
        try:
            body = json.loads(data)
            event_id = body.get("envelope", body).get("event_id")
        except (TypeError, ValueError, AttributeError):
            raise ConsumerAdmissionError("event: invalid envelope JSON") from None
        if not isinstance(event_id, str) or not event_id.strip():
            raise ConsumerAdmissionError("original event_id required")
        return Event(event_id, body)

    def admit(_connection: Any, event: Event, _context: DeliveryContext) -> None:
        decode_projection_event(
            json.dumps(event.body).encode(), expected_world_id=expected_world_id
        )

    def effect(_connection: Any, event: Event, _context: DeliveryContext) -> None:
        apply_delivery(
            projector,
            json.dumps(event.body).encode(),
            expected_world_id=expected_world_id,
        )

    return Consumer(
        ledger=ledger,
        scope=scope,
        connect=connect,
        admit=admit,
        effect=effect,
        identify=identify,
    )


def consumer_configuration(
    *,
    stream: str,
    subject: str,
    durable: str,
    ack_wait_seconds: float,
    max_deliver: int,
) -> dict[str, Any]:
    """Return explicit EVT-003 binding input; does not create or alter a durable."""
    if not all(
        isinstance(value, str) and value.strip() for value in (stream, subject, durable)
    ):
        raise ValueError("stream, subject and durable are required")
    if ack_wait_seconds <= 0 or max_deliver < 1:
        raise ValueError("ack_wait_seconds and max_deliver must be positive")
    return {
        "stream": stream,
        "subject": subject,
        "durable": durable,
        "ack_wait_seconds": ack_wait_seconds,
        "max_deliver": max_deliver,
        "deliver_policy": "all",
    }
