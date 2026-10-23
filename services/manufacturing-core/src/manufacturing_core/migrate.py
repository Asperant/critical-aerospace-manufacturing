"""Ordered Core SQL migrations; does not choose shared platform/CD tooling."""

import hashlib
import os
import sys
from importlib.resources import files

from psycopg import sql

from manufacturing_core.database import connect, require_restricted_role

VERSION = "0001_domain"
VERSIONS = (VERSION, "0002_outbox")
TABLES = (
    "equipment",
    "manufacturing_route",
    "route_visit",
    "production_order",
    "lot",
    "serialized_component",
    "outbox",
)


def migrate(dsn: str, runtime_role: str) -> bool:
    """Return True on application, False on checksum-verified replay.

    Roles and database are supplied by the operator. The migration identity
    needs bootstrap CREATE on this database or ownership of a precreated empty
    core schema. Database-wide bootstrap CREATE should be revoked afterwards.
    """
    sources = [
        files("manufacturing_core").joinpath(f"migrations/{version}.sql").read_text()
        for version in VERSIONS
    ]
    expected = [
        {
            "version": version,
            "sha256": hashlib.sha256(source.encode()).hexdigest(),
            "runtime_role": runtime_role,
        }
        for version, source in zip(VERSIONS, sources, strict=True)
    ]
    with connect(dsn) as conn, conn.transaction():
        conn.execute("SELECT pg_catalog.pg_advisory_xact_lock(731001)")
        require_restricted_role(conn, runtime_role)
        if runtime_role == conn.info.user:
            raise ValueError("migration and runtime roles must differ")
        member = conn.execute(
            "SELECT pg_catalog.pg_has_role(%s, current_user, 'MEMBER') AS member",
            (runtime_role,),
        ).fetchone()
        if member is None or member["member"]:
            raise ValueError("runtime must not inherit the migration identity")
        schema = conn.execute(
            "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner "
            "FROM pg_catalog.pg_namespace WHERE nspname = 'core'"
        ).fetchone()
        if schema is not None and schema["owner"] != conn.info.user:
            raise ValueError("Core schema has an unexpected owner")
        ledger = conn.execute(
            "SELECT to_regclass('core.schema_migration') AS ledger"
        ).fetchone()
        if ledger is None:
            raise ValueError("migration catalog unavailable")
        applied = []
        if ledger["ledger"]:
            applied = conn.execute(
                "SELECT version, sha256, runtime_role FROM core.schema_migration "
                "ORDER BY version"
            ).fetchall()
        if applied != expected[: len(applied)] or len(applied) > len(expected):
            raise ValueError("migration ledger/version/checksum mismatch")
        if applied == expected:
            return False
        for row, source in zip(
            expected[len(applied) :], sources[len(applied) :], strict=True
        ):
            conn.execute(source.encode())
            conn.execute(
                "INSERT INTO core.schema_migration VALUES (%s, %s, %s)",
                (row["version"], row["sha256"], runtime_role),
            )
        conn.execute(
            sql.SQL("GRANT USAGE ON SCHEMA core TO {}").format(
                sql.Identifier(runtime_role)
            )
        )
        for table in TABLES:
            conn.execute(
                sql.SQL("GRANT SELECT, INSERT ON TABLE core.{} TO {}").format(
                    sql.Identifier(table), sql.Identifier(runtime_role)
                )
            )
        return True


def main() -> int:
    try:
        migrate(os.environ["CORE_MIGRATION_DSN"], os.environ["CORE_RUNTIME_ROLE"])
    except Exception:
        # Connection exceptions may contain DSNs. Never print credentials.
        print(
            "Core migration failed; check explicit configuration and role contract",
            file=sys.stderr,
        )
        return 1
    print("Core migrations verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
