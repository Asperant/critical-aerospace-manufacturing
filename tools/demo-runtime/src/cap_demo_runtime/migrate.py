from __future__ import annotations

import os
from pathlib import Path
from typing import LiteralString, cast

import psycopg
from cap_event_consumer.migrate import migrate as migrate_consumer
from manufacturing_core.migrate import migrate as migrate_core
from psycopg import sql
from psycopg.rows import DictRow, dict_row


def _twin_sql() -> str:
    candidates = (
        Path("/app/services/operational-twin/migrations/0001_twin.sql"),
        Path(__file__).resolve().parents[4]
        / "services/operational-twin/migrations/0001_twin.sql",
    )
    for path in candidates:
        if path.is_file():
            return path.read_text()
    raise FileNotFoundError("operational-twin migration SQL is not packaged")


def _dsn(prefix: str, *, host: str, database: str, password: str) -> str:
    return (
        f"postgresql://{os.environ[prefix + '_USER']}:{password}"
        f"@{host}:5432/{database}"
    )


def main() -> None:
    host = os.environ.get("CAP_PG_HOST", "postgres")
    database = os.environ.get("CAP_PG_DATABASE", "cap")
    admin_dsn = os.environ["CAP_PG_ADMIN_DSN"]
    migrator = os.environ.get("CAP_MIGRATION_ROLE", "cap_migrator")
    core_runtime = os.environ.get("CAP_CORE_RUNTIME_ROLE", "cap_core_runtime")
    twin_runtime = os.environ.get("CAP_TWIN_RUNTIME_ROLE", "cap_twin_runtime")
    migrator_password = os.environ["CAP_MIGRATION_PASSWORD"]
    core_password = os.environ["CAP_CORE_RUNTIME_PASSWORD"]
    twin_password = os.environ["CAP_TWIN_RUNTIME_PASSWORD"]
    twin_sql = _twin_sql()

    with psycopg.connect(admin_dsn, autocommit=True) as connection:
        for role, password in (
            (migrator, migrator_password),
            (core_runtime, core_password),
            (twin_runtime, twin_password),
        ):
            exists = connection.execute(
                "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname=%s", (role,)
            ).fetchone()
            if exists is None:
                connection.execute(
                    sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(role), sql.Literal(password)
                    )
                )
            else:
                connection.execute(
                    sql.SQL("ALTER ROLE {} LOGIN PASSWORD {}").format(
                        sql.Identifier(role), sql.Literal(password)
                    )
                )
        connection.execute(
            sql.SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                sql.Identifier(database), sql.Identifier(migrator)
            )
        )

    migration_dsn = _dsn(
        "CAP_MIGRATION", host=host, database=database, password=migrator_password
    )
    migrate_core(migration_dsn, core_runtime)
    with (
        psycopg.Connection[DictRow].connect(
            migration_dsn, row_factory=dict_row
        ) as connection,
        connection.transaction(),
    ):
        for statement in twin_sql.split(";\n"):
            if statement.strip():
                connection.execute(sql.SQL(cast(LiteralString, statement)))
        connection.execute(
            sql.SQL("GRANT USAGE ON SCHEMA twin TO {}").format(
                sql.Identifier(twin_runtime)
            )
        )
        for table in ("projection_entity", "applied_event", "projection_revision"):
            connection.execute(
                sql.SQL("GRANT SELECT, INSERT, UPDATE ON TABLE twin.{} TO {}").format(
                    sql.Identifier(table), sql.Identifier(twin_runtime)
                )
            )
        connection.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {} AUTHORIZATION {}").format(
                sql.Identifier("twin_consumer"), sql.Identifier(migrator)
            )
        )
        connection.execute(
            sql.SQL("REVOKE ALL ON SCHEMA {} FROM PUBLIC").format(
                sql.Identifier("twin_consumer")
            )
        )
        migrate_consumer(connection, "twin_consumer", twin_runtime)
    Path("/tmp/cap-demo-migrate.done").touch()
    print("demo runtime migrations verified")


if __name__ == "__main__":
    main()
