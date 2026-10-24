"""Scoped additive migration; preserves the original Core migration contract."""

import hashlib
import os
import sys
from importlib.resources import files

from psycopg import sql

from manufacturing_core.database import connect
from manufacturing_core.migrate import migrate as migrate_domain

VERSION = "0002_rework_history"
TABLES = (
    "rework_history",
    "rework_directive",
    "rework_segment",
    "rework_route_visit",
    "rework_execution",
)


def migrate(dsn: str, runtime_role: str) -> bool:
    """Verify base migration, then atomically apply/replay only rework storage.

    The unchanged base runner checks the schema owner, role separation and its
    checksum ledger. Both runners use the same transaction advisory lock.
    """
    migrate_domain(dsn, runtime_role)
    source = (
        files("manufacturing_core").joinpath(f"migrations/{VERSION}.sql").read_text()
    )
    digest = hashlib.sha256(source.encode()).hexdigest()
    with connect(dsn) as conn, conn.transaction():
        conn.execute("SELECT pg_catalog.pg_advisory_xact_lock(731001)")
        ledger = conn.execute(
            "SELECT to_regclass('core.rework_schema_migration') AS ledger"
        ).fetchone()
        if ledger is None:
            raise ValueError("rework migration catalog unavailable")
        if ledger["ledger"]:
            applied = conn.execute(
                "SELECT version, sha256, runtime_role FROM core.rework_schema_migration"
            ).fetchall()
            if applied != [
                {"version": VERSION, "sha256": digest, "runtime_role": runtime_role}
            ]:
                raise ValueError("rework migration ledger/version/checksum mismatch")
            return False
        conn.execute(source.encode())
        conn.execute(
            "INSERT INTO core.rework_schema_migration VALUES (%s, %s, %s)",
            (VERSION, digest, runtime_role),
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
        print(
            "Core rework migration failed; check explicit configuration and role contract",
            file=sys.stderr,
        )
        return 1
    print("Core rework migration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
