"""Single initial SQL migration; does not choose shared platform/CD tooling."""

import hashlib
import os
import sys
from importlib.resources import files

from psycopg import sql

from manufacturing_core.database import connect, require_restricted_role

VERSION = "0001_domain"
TABLES = (
    "equipment",
    "manufacturing_route",
    "route_visit",
    "production_order",
    "lot",
    "serialized_component",
)


def migrate(dsn: str, runtime_role: str) -> bool:
    """Return True on application, False on checksum-verified replay.

    Roles and database are supplied by the operator. The migration identity
    needs bootstrap CREATE on this database or ownership of a precreated empty
    core schema. Database-wide bootstrap CREATE should be revoked afterwards.
    """
    source = (
        files("manufacturing_core").joinpath("migrations/0001_domain.sql").read_text()
    )
    digest = hashlib.sha256(source.encode()).hexdigest()
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
        if ledger["ledger"]:
            applied = conn.execute(
                "SELECT version, sha256, runtime_role FROM core.schema_migration"
            ).fetchall()
            if applied != [
                {"version": VERSION, "sha256": digest, "runtime_role": runtime_role}
            ]:
                raise ValueError("migration ledger/version/checksum mismatch")
            return False
        conn.execute(source.encode())
        conn.execute(
            "INSERT INTO core.schema_migration VALUES (%s, %s, %s)",
            (VERSION, digest, runtime_role),
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
    print("Core initial migration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
