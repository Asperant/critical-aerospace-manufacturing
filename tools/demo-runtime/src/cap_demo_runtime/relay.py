from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from pathlib import Path
from typing import Any

import nats
import psycopg
from manufacturing_core.outbox import OutboxRepository
from psycopg.rows import DictRow, dict_row

from .config import Settings


async def _ensure_stream(js: Any, settings: Settings) -> None:
    try:
        info = await js.stream_info(settings.stream)
        if settings.subject not in info.config.subjects:
            raise RuntimeError(
                "existing event stream does not bind the approved subject"
            )
    except Exception as exc:
        if exc.__class__.__name__ != "NotFoundError":
            raise
        await js.add_stream(name=settings.stream, subjects=[settings.subject])


async def run() -> None:
    settings = Settings.from_env()
    nc = await nats.connect(settings.nats_url)
    js = nc.jetstream()
    await _ensure_stream(js, settings)
    Path("/tmp/cap-demo-relay.ready").touch()
    try:
        while True:
            with psycopg.Connection[DictRow].connect(
                settings.pg_dsn, row_factory=dict_row, connect_timeout=10
            ) as connection:
                records = OutboxRepository(connection).pending(limit=25)
                for record in records:
                    event = record.event.model_dump(mode="json")
                    envelope = {
                        key: value for key, value in event.items() if key != "payload"
                    }
                    data = json.dumps(
                        {"envelope": envelope, "payload": event["payload"]},
                        separators=(",", ":"),
                    ).encode()
                    await js.publish(settings.subject, data)
                    with connection.transaction():
                        OutboxRepository(connection).mark_published(record.outbox_id)
            await asyncio.sleep(0.25)
    finally:
        await nc.drain()


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        asyncio.run(run())
