"""Synthetic test adapter only; not any application's business policy."""

import psycopg
from cap_event_consumer.consumer import AdmissionError, Consumer, DeliveryContext, Event
from cap_event_consumer.ledger import ProcessedMessageLedger
from psycopg.rows import DictRow, dict_row


def make_consumer(
    dsn: str, scope: str = "test/live", *, replay: bool = False
) -> Consumer:
    def connect() -> psycopg.Connection[DictRow]:
        return psycopg.Connection[DictRow].connect(dsn, row_factory=dict_row)

    def admit(
        conn: psycopg.Connection[DictRow], event: Event, context: DeliveryContext
    ) -> None:
        # Test-only published input contract and conservative gap rejection hook.
        # No application ordering/gap policy is implemented by the framework.
        if event.body.get("aggregate_version", 1) != 1:
            raise AdmissionError("test adapter requires reconciliation for version gap")
        if context.replay and context.target != "shadow-test":
            raise AdmissionError("test replay target not admitted")

    def effect(
        conn: psycopg.Connection[DictRow], event: Event, context: DeliveryContext
    ) -> None:
        conn.execute("INSERT INTO consumer.effect VALUES (%s)", (event.event_id,))
        if event.body.get("fail"):
            raise RuntimeError("injected callback failure")

    return Consumer(
        ProcessedMessageLedger("consumer"),
        scope,
        connect,
        admit,
        effect,
        allow_replay=replay,
    )
