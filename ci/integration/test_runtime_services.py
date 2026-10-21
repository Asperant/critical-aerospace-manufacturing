"""WP-CICD-001 integration-tier smoke against REAL PostgreSQL and NATS JetStream.

Boundary mode REAL: no in-memory database or fake bus (CI-INV-07, 01 Item 41
§46–47, §52). Start the services with ``ci/scripts/integration_services.sh up``
and export the printed ``CI_PG_DSN`` / ``CI_NATS_URL``. Missing configuration is
a failure, never a skip, so the tier cannot pass without real services.
"""

# nats-py ships incomplete type information; keep strict mode for everything else.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false

from __future__ import annotations

import asyncio
import os
import uuid

import nats
import psycopg
import pytest

pytestmark = pytest.mark.integration


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        pytest.fail(
            f"{name} is not set; start services with "
            "`ci/scripts/integration_services.sh up` and export its output."
        )
    return value


def test_postgresql_round_trip() -> None:
    dsn = _required_env("CI_PG_DSN")
    marker = uuid.uuid4().hex
    with psycopg.connect(dsn, connect_timeout=10) as conn, conn.cursor() as cur:
        cur.execute("SHOW server_version_num")
        row = cur.fetchone()
        assert row is not None
        assert int(row[0]) >= 160000, "PostgreSQL 16+ is the canonical store"
        cur.execute("CREATE TEMP TABLE ci_smoke (id text PRIMARY KEY, body text)")
        cur.execute("INSERT INTO ci_smoke VALUES (%s, %s)", (marker, "ok"))
        cur.execute("SELECT body FROM ci_smoke WHERE id = %s", (marker,))
        assert cur.fetchone() == ("ok",)


async def _jetstream_round_trip(url: str) -> bytes:
    suffix = uuid.uuid4().hex[:12]
    stream, subject = f"CI_SMOKE_{suffix}", f"ci.smoke.{suffix}"
    nc = await nats.connect(url, connect_timeout=10)
    try:
        js = nc.jetstream()
        await js.add_stream(name=stream, subjects=[subject])
        try:
            ack = await js.publish(subject, b"wp-cicd-001")
            assert ack.stream == stream
            assert ack.seq == 1
            sub = await js.pull_subscribe(subject, durable=f"ci_{suffix}")
            messages = await sub.fetch(1, timeout=10)
            await messages[0].ack()
            return messages[0].data
        finally:
            await js.delete_stream(stream)
    finally:
        await nc.drain()


def test_nats_jetstream_persisted_round_trip() -> None:
    url = _required_env("CI_NATS_URL")
    assert asyncio.run(_jetstream_round_trip(url)) == b"wp-cicd-001"
