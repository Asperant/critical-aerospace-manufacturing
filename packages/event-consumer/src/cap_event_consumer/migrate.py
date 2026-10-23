"""Versioned SQL/checksum convention; no service imports or shared schema owner."""

import hashlib
from importlib.resources import files
from typing import LiteralString, cast

from psycopg import Connection, sql
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow

VERSION = "0001_processed_message"


def migrate(connection: Connection[DictRow], schema: str, runtime_role: str) -> bool:
    """Stage the migration in a caller-owned transaction; False on verified replay.

    Caller provisions a private schema owned by its separate migration identity.
    Runtime receives only schema USAGE and ledger SELECT/INSERT. No role, database
    or infrastructure is provisioned by this package.
    """
    if connection.info.transaction_status != TransactionStatus.INTRANS:
        raise ValueError("an active caller-owned migration transaction is required")
    if connection.info.server_version < 180000:
        raise ValueError("PostgreSQL 18 or newer is required")
    if not schema.strip() or not runtime_role.strip():
        raise ValueError("explicit private schema and runtime role required")
    roles = connection.execute(
        "SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolreplication, "
        "rolbypassrls FROM pg_catalog.pg_roles WHERE rolname IN (current_user, %s)",
        (runtime_role,),
    ).fetchall()
    if len(roles) != 2 or any(
        row[field]
        for row in roles
        for field in (
            "rolsuper",
            "rolcreatedb",
            "rolcreaterole",
            "rolreplication",
            "rolbypassrls",
        )
    ):
        raise ValueError("distinct restricted migration/runtime roles required")
    ownership = connection.execute(
        "SELECT pg_catalog.pg_get_userbyid(nspowner) = current_user AS owned, "
        "pg_catalog.pg_has_role(%s, current_user, 'MEMBER') AS member "
        "FROM pg_catalog.pg_namespace WHERE nspname = %s",
        (runtime_role, schema),
    ).fetchone()
    if ownership is None or not ownership["owned"] or ownership["member"]:
        raise ValueError("private migration-owned schema and separate runtime required")
    connection.execute(
        "SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(%s, 0))",
        ("cap-event-consumer:migration:" + schema,),
    )
    source = (
        files("cap_event_consumer")
        .joinpath("migrations/0001_processed_message.sql")
        .read_text()
    )
    digest = hashlib.sha256(source.encode()).hexdigest()
    existing = connection.execute(
        "SELECT pg_catalog.to_regclass(%s) AS ledger",
        (sql.Identifier(schema, "consumer_schema_migration").as_string(connection),),
    ).fetchone()
    if existing and existing["ledger"]:
        rows = connection.execute(
            sql.SQL(
                "SELECT version, sha256, runtime_role FROM {}.consumer_schema_migration"
            ).format(sql.Identifier(schema))
        ).fetchall()
        if rows != [
            {"version": VERSION, "sha256": digest, "runtime_role": runtime_role}
        ]:
            raise ValueError("consumer migration ledger/version/checksum mismatch")
        return False
    # Trusted package SQL template; the operator's identifier is quoted separately.
    connection.execute(
        sql.SQL(cast(LiteralString, source)).format(schema=sql.Identifier(schema))
    )
    connection.execute(
        sql.SQL("INSERT INTO {}.consumer_schema_migration VALUES (%s, %s, %s)").format(
            sql.Identifier(schema)
        ),
        (VERSION, digest, runtime_role),
    )
    connection.execute(
        sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
            sql.Identifier(schema), sql.Identifier(runtime_role)
        )
    )
    connection.execute(
        sql.SQL("GRANT SELECT, INSERT ON {}.processed_message TO {}").format(
            sql.Identifier(schema), sql.Identifier(runtime_role)
        )
    )
    return True
