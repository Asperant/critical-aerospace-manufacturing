"""Versioned Core migration runner with inspectable status and checksums."""

import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from alembic import command
from alembic.config import Config
from psycopg.conninfo import conninfo_to_dict
from sqlalchemy.engine import URL

from manufacturing_core.database import connect, require_restricted_role

VERSION = "0007_lot_lineage"
REWORK_TABLES = (
    "rework_history",
    "rework_directive",
    "rework_segment",
    "rework_route_visit",
    "rework_execution",
)
LINEAGE_TABLES = (
    "lineage_history",
    "lineage_event",
    "lineage_lot",
    "lineage_membership",
    "lineage_parent",
)
TABLES = (
    "equipment",
    "manufacturing_route",
    "route_visit",
    "production_order",
    "lot",
    "serialized_component",
    "production_order_state",
    "lot_state",
    "serialized_component_state",
    "command_idempotency",
    "command_outcome",
    "material_hold",
    "lot_event_sequence",
    "outbox",
    *REWORK_TABLES,
    *LINEAGE_TABLES,
)


def sqlalchemy_url(dsn: str) -> str:
    """Convert either libpq keyword DSNs or URLs without string interpolation."""
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    if dsn.startswith("postgres://"):
        return dsn.replace("postgres://", "postgresql+psycopg://", 1)
    fields = conninfo_to_dict(dsn)

    def field(name: str) -> str | None:
        value = fields.get(name)
        return value if isinstance(value, str) else None

    port_value = field("port")
    url_create = cast(Any, URL).create
    return url_create(
        "postgresql+psycopg",
        username=field("user"),
        password=field("password"),
        host=field("host"),
        port=int(port_value) if port_value is not None else None,
        database=field("dbname"),
    ).render_as_string(hide_password=False)


@dataclass(frozen=True)
class MigrationStatus:
    version: str
    sha256: str
    runtime_role: str


def status(dsn: str) -> list[MigrationStatus]:
    """Read the migration ledger without changing database state."""
    with connect(dsn) as conn:
        ledger = conn.execute(
            "SELECT version, sha256, runtime_role FROM core.schema_migration "
            "ORDER BY version"
        ).fetchall()
    return [MigrationStatus(**row) for row in ledger]


def migrate(dsn: str, runtime_role: str) -> bool:
    """Return True on application, False on checksum-verified replay.

    Roles and database are supplied by the operator. The migration identity
    needs bootstrap CREATE on this database or ownership of a precreated empty
    core schema. Database-wide bootstrap CREATE should be revoked afterwards.
    """
    migration_sources = tuple(
        (version, files("manufacturing_core").joinpath(filename).read_text())
        for version, filename in (
            ("0001_domain", "migrations/0001_domain.sql"),
            ("0002_command_acceptance", "migrations/0002_command_acceptance.sql"),
            ("0003_lifecycle", "migrations/0003_lifecycle.sql"),
            ("0004_material_hold", "migrations/0004_material_hold.sql"),
            ("0005_outbox", "migrations/0005_outbox.sql"),
            ("0006_rework_history", "migrations/0006_rework_history.sql"),
            ("0007_lot_lineage", "migrations/0007_lot_lineage.sql"),
        )
    )
    expected = [
        {
            "version": version,
            "sha256": hashlib.sha256(source.encode()).hexdigest(),
            "runtime_role": runtime_role,
        }
        for version, source in migration_sources
    ]
    with connect(dsn) as preflight, preflight.transaction():
        preflight.execute("SELECT pg_catalog.pg_advisory_xact_lock(731001)")
        require_restricted_role(preflight, runtime_role)
        if runtime_role == preflight.info.user:
            raise ValueError("migration and runtime roles must differ")
        member = preflight.execute(
            "SELECT pg_catalog.pg_has_role(%s, current_user, 'MEMBER') AS member",
            (runtime_role,),
        ).fetchone()
        if member is None or member["member"]:
            raise ValueError("runtime must not inherit the migration identity")
        schema = preflight.execute(
            "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner "
            "FROM pg_catalog.pg_namespace WHERE nspname = 'core'"
        ).fetchone()
        if schema is not None and schema["owner"] != preflight.info.user:
            raise ValueError("Core schema has an unexpected owner")
        ledger_ref = preflight.execute(
            "SELECT to_regclass('core.schema_migration') AS ledger"
        ).fetchone()
        ledger = (
            preflight.execute(
                "SELECT version, sha256, runtime_role FROM core.schema_migration "
                "ORDER BY version"
            ).fetchall()
            if ledger_ref is not None and ledger_ref["ledger"]
            else []
        )
        if ledger:
            if len(ledger) > len(expected) or ledger != expected[: len(ledger)]:
                raise ValueError("migration ledger/version/checksum mismatch")
            if len(ledger) == len(expected):
                return False
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url(dsn))
    config.attributes["runtime_role"] = runtime_role
    command.upgrade(config, "head")
    return True


def main() -> int:
    try:
        dsn = os.environ["CORE_MIGRATION_DSN"]
        if "--status" in sys.argv[1:]:
            print(
                json.dumps([asdict(record) for record in status(dsn)], sort_keys=True)
            )
            return 0
        migrate(dsn, os.environ["CORE_RUNTIME_ROLE"])
    except Exception:
        # Connection exceptions may contain DSNs. Never print credentials.
        print(
            "Core migration failed; check explicit configuration and role contract",
            file=sys.stderr,
        )
        return 1
    print("Core migration verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
