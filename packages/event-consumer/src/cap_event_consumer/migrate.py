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


def migrate_owned_schema(
    connection: Connection[DictRow],
    schema: str,
    runtime_role: str,
    version: str,
    source: str,
    table_name: str,
    *,
    update_columns: tuple[str, ...] = (),
) -> bool:
    """Apply one service-owned SQL migration using its private-schema owner.

    The migration remains service-owned; this shared boundary supplies checksum,
    replay and restricted runtime-grant handling without leaking a DB driver into
    the service package.
    """
    if connection.info.transaction_status != TransactionStatus.INTRANS:
        raise ValueError("an active caller-owned migration transaction is required")
    if connection.info.server_version < 180000:
        raise ValueError("PostgreSQL 18 or newer is required")
    if not all(value.strip() for value in (schema, runtime_role, version, table_name)):
        raise ValueError("explicit schema, runtime role, version and table required")
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
        (f"cap-event-consumer:migration:{schema}:{version}",),
    )
    digest = hashlib.sha256(source.encode()).hexdigest()
    migration_table = sql.Identifier(schema, "schema_migration")
    existing = connection.execute(
        "SELECT pg_catalog.to_regclass(%s) AS migration_table",
        (migration_table.as_string(connection),),
    ).fetchone()
    if existing is not None and existing["migration_table"] is not None:
        rows = connection.execute(
            sql.SQL(
                "SELECT version, sha256, runtime_role FROM {}.schema_migration"
            ).format(sql.Identifier(schema))
        ).fetchall()
        if rows != [
            {"version": version, "sha256": digest, "runtime_role": runtime_role}
        ]:
            raise ValueError("service migration ledger/version/checksum mismatch")
        table = connection.execute(
            "SELECT pg_catalog.to_regclass(%s) AS migrated_table",
            (sql.Identifier(schema, table_name).as_string(connection),),
        ).fetchone()
        if table is None or table["migrated_table"] is None:
            raise ValueError("service migration is recorded but its table is missing")
        return False

    connection.execute(
        sql.SQL(cast(LiteralString, source)).format(schema=sql.Identifier(schema))
    )
    connection.execute(
        sql.SQL("INSERT INTO {}.schema_migration VALUES (%s, %s, %s)").format(
            sql.Identifier(schema)
        ),
        (version, digest, runtime_role),
    )
    connection.execute(
        sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
            sql.Identifier(schema), sql.Identifier(runtime_role)
        )
    )
    connection.execute(
        sql.SQL("GRANT SELECT, INSERT ON {}.{} TO {}").format(
            sql.Identifier(schema),
            sql.Identifier(table_name),
            sql.Identifier(runtime_role),
        )
    )
    if update_columns:
        connection.execute(
            sql.SQL("GRANT UPDATE ({}) ON {}.{} TO {}").format(
                sql.SQL(", ").join(map(sql.Identifier, update_columns)),
                sql.Identifier(schema),
                sql.Identifier(table_name),
                sql.Identifier(runtime_role),
            )
        )
    return True
