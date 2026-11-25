"""Install the Vision outbox and the shared processed-message ledger.

The caller owns the migration transaction and provisions both private schemas
under a separate migration role. Runtime permissions are column-scoped.
"""

from __future__ import annotations

import hashlib
from importlib.resources import files
from typing import LiteralString, cast

from cap_event_consumer.migrate import migrate as migrate_consumer
from psycopg import Connection, sql
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow

VERSION = "0001_inspection_observation_outbox"
VISION_SCHEMA = "vision"
CONSUMER_SCHEMA = "vision_consumer"


def migrate(connection: Connection[DictRow], runtime_role: str) -> bool:
    """Stage both migrations in an active caller-owned transaction."""
    if connection.info.transaction_status != TransactionStatus.INTRANS:
        raise ValueError("an active caller-owned migration transaction is required")
    if connection.info.server_version < 180000:
        raise ValueError("PostgreSQL 18 or newer is required")
    if not runtime_role.strip():
        raise ValueError("explicit restricted runtime role required")
    ownership = connection.execute(
        "SELECT pg_catalog.pg_get_userbyid(nspowner) = current_user AS owned, "
        "pg_catalog.pg_has_role(%s, current_user, 'MEMBER') AS member "
        "FROM pg_catalog.pg_namespace WHERE nspname = %s",
        (runtime_role, VISION_SCHEMA),
    ).fetchone()
    if ownership is None or not ownership["owned"] or ownership["member"]:
        raise ValueError("private Vision schema and separate runtime role required")

    # The shared package enforces its own private schema and restricted runtime
    # grants. Both records and the service outbox commit or roll back together.
    consumer_changed = migrate_consumer(connection, CONSUMER_SCHEMA, runtime_role)
    connection.execute(
        "SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(%s, 0))",
        ("vision-service:migration:" + VERSION,),
    )
    source = (
        files("vision_service")
        .joinpath("migrations/0001_inspection_observation_outbox.sql")
        .read_text(encoding="utf-8")
    )
    digest = hashlib.sha256(source.encode()).hexdigest()
    existing = connection.execute(
        "SELECT pg_catalog.to_regclass(%s) AS migration_table",
        (sql.Identifier(VISION_SCHEMA, "schema_migration").as_string(connection),),
    ).fetchone()
    changed = False
    if existing is not None and existing["migration_table"] is not None:
        rows = connection.execute(
            sql.SQL(
                "SELECT version, sha256, runtime_role FROM {}.schema_migration"
            ).format(sql.Identifier(VISION_SCHEMA))
        ).fetchall()
        expected = [
            {"version": VERSION, "sha256": digest, "runtime_role": runtime_role}
        ]
        if rows != expected:
            raise ValueError("Vision migration ledger/version/checksum mismatch")
        outbox_exists = connection.execute(
            "SELECT pg_catalog.to_regclass(%s) AS outbox_table",
            (
                sql.Identifier(
                    VISION_SCHEMA, "inspection_observation_outbox"
                ).as_string(connection),
            ),
        ).fetchone()
        if outbox_exists is None or outbox_exists["outbox_table"] is None:
            raise ValueError("Vision outbox migration is recorded but table is missing")
    else:
        connection.execute(sql.SQL(cast(LiteralString, source)))
        connection.execute(
            sql.SQL("INSERT INTO {}.schema_migration VALUES (%s, %s, %s)").format(
                sql.Identifier(VISION_SCHEMA)
            ),
            (VERSION, digest, runtime_role),
        )
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                sql.Identifier(VISION_SCHEMA), sql.Identifier(runtime_role)
            )
        )
        connection.execute(
            sql.SQL(
                "GRANT SELECT, INSERT ON {}.inspection_observation_outbox TO {}"
            ).format(sql.Identifier(VISION_SCHEMA), sql.Identifier(runtime_role))
        )
        connection.execute(
            sql.SQL(
                "GRANT UPDATE (published_at, attempt_count, claim_token, claimed_until) "
                "ON {}.inspection_observation_outbox TO {}"
            ).format(sql.Identifier(VISION_SCHEMA), sql.Identifier(runtime_role))
        )
        changed = True
    return consumer_changed or changed
