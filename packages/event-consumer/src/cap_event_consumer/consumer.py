"""Transport-neutral, local-commit-before-ACK consumer boundary."""

import asyncio
import json
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Protocol

from psycopg import Connection
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow

from cap_event_consumer.ledger import Outcome, ProcessedMessageLedger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    event_id: str
    body: Mapping[str, object]


@dataclass(frozen=True)
class DeliveryContext:
    """Trusted adapter configuration, never derived from untrusted payload flags."""

    replay: bool = False
    replay_id: str | None = None
    target: str | None = None


class Delivery(Protocol):
    @property
    def data(self) -> bytes: ...
    async def ack(self) -> None: ...
    async def nak(self) -> None: ...


class AdmissionError(ValueError):
    """Adapter must resolve invalid context/order; no destructive fallback."""


def identify_json(data: bytes) -> Event:
    """Minimum identity validation only; adapter validates its published contract."""
    body = json.loads(data)
    if not isinstance(body, dict):
        raise AdmissionError("event must be an object")
    identity = body.get("event_id")
    if not isinstance(identity, str) or not identity.strip():
        raise AdmissionError("original event_id required")
    return Event(identity, body)


@dataclass
class Consumer:
    """One connection/transaction per delivery; business admission stays explicit.

    connect must return an IDLE connection exclusively owned by this delivery.
    admit validates schema/world/order and effects use only the supplied local
    transaction. The lower-level ledger API remains caller-transaction-owned.
    No retry loop, retention, domain transitions or broker routing lives here.
    """

    ledger: ProcessedMessageLedger
    scope: str
    connect: Callable[[], Connection[DictRow]]
    admit: Callable[[Connection[DictRow], Event, DeliveryContext], None]
    effect: Callable[[Connection[DictRow], Event, DeliveryContext], None]
    identify: Callable[[bytes], Event] = identify_json
    allow_replay: bool = False
    _counts: dict[str, int] = field(default_factory=dict, init=False)

    def _apply(self, event: Event, context: DeliveryContext) -> Outcome:
        with self.connect() as connection:
            if connection.info.transaction_status != TransactionStatus.IDLE:
                raise ValueError(
                    "delivery connection must be idle and exclusively owned"
                )
            with connection.transaction():

                def local_effect(conn: Connection[DictRow]) -> None:
                    self.admit(conn, event, context)
                    self.effect(conn, event, context)

                outcome = self.ledger.process(
                    connection, self.scope, event.event_id, local_effect
                )
            # The transaction manager has successfully committed here.
            return outcome

    async def handle(self, delivery: Delivery, context: DeliveryContext) -> Outcome:
        started = time.monotonic()
        try:
            if context.replay and (
                not self.allow_replay or not context.replay_id or not context.target
            ):
                raise AdmissionError(
                    "replay requires an admitted isolated target and ReplayRun"
                )
            event = self.identify(delivery.data)
            if not event.event_id.strip():
                raise AdmissionError("original event_id required")
            worker = asyncio.create_task(asyncio.to_thread(self._apply, event, context))
            try:
                outcome = await asyncio.shield(worker)
            except asyncio.CancelledError:
                # A thread cannot be killed. Settle its transaction but never ACK
                # this cancelled delivery; committed work is safe on redelivery.
                try:
                    await worker
                except Exception:
                    logger.warning(
                        "consumer cancelled transaction failed",
                        extra={"consumer_scope": self.scope},
                    )
                raise
        except asyncio.CancelledError:
            self._counts["cancelled"] = self._counts.get("cancelled", 0) + 1
            raise
        except Exception:
            self._counts["failed"] = self._counts.get("failed", 0) + 1
            logger.warning(
                "consumer processing failed", extra={"consumer_scope": self.scope}
            )
            await delivery.nak()
            raise
        # ACK failure/cancellation is deliberately outside processing-failure NAK:
        # commit may already be durable. Redelivery must consult the ledger.
        try:
            await delivery.ack()
        except BaseException:
            self._counts["ack_failed"] = self._counts.get("ack_failed", 0) + 1
            raise
        self._counts[outcome.value] = self._counts.get(outcome.value, 0) + 1
        logger.info(
            "consumer delivery completed",
            extra={
                "consumer_scope": self.scope,
                "event_id": event.event_id,
                "correlation_id": event.body.get("correlation_id"),
                "outcome": outcome.value,
                "duration_seconds": time.monotonic() - started,
            },
        )
        return outcome

    def health(self) -> dict[str, object]:
        """Local outcomes only; does not assert broker or database readiness."""
        return {"consumer_scope": self.scope, "delivery_counts": dict(self._counts)}
