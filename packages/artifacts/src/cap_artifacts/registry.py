"""Relational artifact registry and cross-store consistency (WP-OBJ-001, slice 3).

The registry is the metadata half of 02 "Object != Artifact": one row per
artifact version in PostgreSQL, the bytes in object storage. Its primary key
makes a version write-once even when writers race; a trigger keeps identity and
content immutable and allows only the 02 lifecycle transitions. The migration
follows the Core pattern: a separate migration identity owns the schema, the
runtime identity gets only SELECT/INSERT/UPDATE (no DELETE, no DDL), and a
checksummed ledger makes replays verifiable.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from typing import Any, LiteralString, cast

import psycopg
from psycopg import errors, sql
from psycopg.rows import DictRow, dict_row

from cap_artifacts.conventions import BUCKETS
from cap_artifacts.errors import OverwriteError, StoreError
from cap_artifacts.reference import ArtifactReference

VERSION = "0001_registry"
SCHEMA = "artifact"
LOCK_KEY = 731_301
RUNTIME_TABLES: dict[str, LiteralString] = {
    "artifact_version": "SELECT, INSERT, UPDATE",
    "lifecycle_transition": "SELECT",
}


class RegistryError(StoreError):
    """The registry refused an operation or is misconfigured."""


class DuplicateVersionError(OverwriteError):
    """The artifact version is already registered: versions are write-once."""


def _connect(dsn: str) -> psycopg.Connection[DictRow]:
    if not dsn.strip():
        raise RegistryError("explicit artifact registry DSN required")
    conn = psycopg.Connection[DictRow].connect(
        dsn, row_factory=dict_row, connect_timeout=10
    )
    try:
        conn.execute("SET search_path TO pg_catalog")
        _require_restricted(conn, conn.info.user)
        conn.commit()
    except Exception:
        conn.close()
        raise
    return conn


def _require_restricted(conn: psycopg.Connection[DictRow], role: str) -> None:
    row = conn.execute(
        "SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls "
        "FROM pg_catalog.pg_roles WHERE rolname = %s",
        (role,),
    ).fetchone()
    if row is None or any(row.values()):
        raise RegistryError("registry role is missing or has administrative privileges")


def migrate(dsn: str, runtime_role: str) -> bool:
    """Apply the registry schema; True when applied, False on a verified replay."""
    source = (
        files("cap_artifacts").joinpath(f"migrations/{VERSION}.sql").read_text("utf-8")
    )
    digest = hashlib.sha256(source.encode()).hexdigest()
    with _connect(dsn) as conn, conn.transaction():
        conn.execute("SELECT pg_catalog.pg_advisory_xact_lock(%s)", (LOCK_KEY,))
        _require_restricted(conn, runtime_role)
        if runtime_role == conn.info.user:
            raise RegistryError("migration and runtime roles must differ")
        member = conn.execute(
            "SELECT pg_catalog.pg_has_role(%s, current_user, 'MEMBER') AS member",
            (runtime_role,),
        ).fetchone()
        if member is None or member["member"]:
            raise RegistryError("runtime must not inherit the migration identity")
        owner = conn.execute(
            "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner "
            "FROM pg_catalog.pg_namespace WHERE nspname = %s",
            (SCHEMA,),
        ).fetchone()
        if owner is not None and owner["owner"] != conn.info.user:
            raise RegistryError("artifact schema has an unexpected owner")
        ledger = conn.execute(
            "SELECT to_regclass('artifact.schema_migration') AS t"
        ).fetchone()
        if ledger is not None and ledger["t"]:
            applied = conn.execute(
                "SELECT version, sha256, runtime_role FROM artifact.schema_migration"
            ).fetchall()
            expected = {
                "version": VERSION,
                "sha256": digest,
                "runtime_role": runtime_role,
            }
            if applied != [expected]:
                raise RegistryError("migration ledger/version/checksum mismatch")
            return False
        conn.execute(cast(Any, source.encode()))
        conn.execute(
            "INSERT INTO artifact.schema_migration VALUES (%s, %s, %s)",
            (VERSION, digest, runtime_role),
        )
        role = sql.Identifier(runtime_role)
        conn.execute(sql.SQL("GRANT USAGE ON SCHEMA artifact TO {}").format(role))
        for table, privileges in RUNTIME_TABLES.items():
            conn.execute(
                sql.SQL("GRANT " + privileges + " ON TABLE artifact.{} TO {}").format(
                    sql.Identifier(table), role
                )
            )
    return True


class Registry:
    """Runtime access to artifact.artifact_version (no DDL, no DELETE)."""

    def __init__(self, conn: psycopg.Connection[DictRow]) -> None:
        self.conn = conn

    @classmethod
    def connect(cls, dsn: str) -> Registry:
        conn = _connect(dsn)
        try:
            row = conn.execute(
                "SELECT pg_catalog.pg_get_userbyid(nspowner) AS owner, "
                "pg_catalog.has_schema_privilege(current_user, oid, 'CREATE') AS ddl "
                "FROM pg_catalog.pg_namespace WHERE nspname = %s",
                (SCHEMA,),
            ).fetchone()
            if row is None or row["ddl"] or row["owner"] == conn.info.user:
                raise RegistryError(
                    "runtime requires an existing, separately owned artifact schema"
                )
            conn.commit()
        except Exception:
            conn.close()
            raise
        conn.autocommit = True
        return cls(conn)

    def close(self) -> None:
        self.conn.close()

    def reserve(self, ref: ArtifactReference) -> None:
        """Register a RESERVED version; a second reservation of it is refused."""
        data = ref.to_dict()
        checksum = cast(dict[str, str], data["checksum"])
        storage = cast(dict[str, str], data["storage"])
        try:
            self.conn.execute(
                "INSERT INTO artifact.artifact_version (artifact_id, version, artifact_type, "
                "retention_class, bucket, object_key, object_id, size_bytes, checksum_algorithm, "
                "checksum_value, lifecycle_status, reference) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
                (
                    data["artifact_id"],
                    data["version"],
                    data["artifact_type"],
                    data["retention_class"],
                    storage["bucket"],
                    storage["key"],
                    storage["object_id"],
                    data["size_bytes"],
                    checksum["algorithm"],
                    checksum["value"],
                    data["lifecycle_status"],
                    json.dumps(data),
                ),
            )
        except errors.UniqueViolation:
            raise DuplicateVersionError(
                f"artifact {data['artifact_id']} v{data['version']} is already registered; "
                "new bytes need a new version"
            ) from None
        except errors.CheckViolation as exc:
            raise RegistryError(
                f"registry refused the reservation: {exc.diag.message_primary}"
            ) from None

    def transition(self, ref: ArtifactReference, status: str) -> ArtifactReference:
        """Move a version to `status` only if the registry still holds `ref`'s status."""
        moved = ref.with_status(status)  # same rule as the database trigger
        try:
            row = self.conn.execute(
                "UPDATE artifact.artifact_version SET lifecycle_status = %s, reference = %s::jsonb "
                "WHERE artifact_id = %s AND version = %s AND lifecycle_status = %s RETURNING version",
                (
                    status,
                    json.dumps(moved.to_dict()),
                    ref.artifact_id,
                    ref.data["version"],
                    ref.lifecycle_status,
                ),
            ).fetchone()
        except errors.CheckViolation as exc:
            raise RegistryError(
                f"registry refused the transition: {exc.diag.message_primary}"
            ) from None
        if row is None:
            raise RegistryError(
                f"artifact {ref.artifact_id} v{ref.data['version']} is no longer "
                f"{ref.lifecycle_status}; reload it before changing it"
            )
        return moved

    def get(self, artifact_id: str, version: int) -> ArtifactReference | None:
        row = self.conn.execute(
            "SELECT reference FROM artifact.artifact_version WHERE artifact_id = %s AND version = %s",
            (artifact_id, version),
        ).fetchone()
        return None if row is None else ArtifactReference.from_dict(row["reference"])

    def rows(self) -> Iterator[dict[str, Any]]:
        cursor = self.conn.execute(
            "SELECT artifact_id::text, version, bucket, object_key, lifecycle_status, updated_at "
            "FROM artifact.artifact_version ORDER BY bucket, object_key"
        )
        yield from cursor


@dataclass
class ConsistencyReport:
    """02 bidirectional integrity: metadata without bytes, bytes without metadata."""

    missing_bytes: list[str] = field(default_factory=list)
    orphan_objects: list[str] = field(default_factory=list)
    stale_in_flight: list[str] = field(default_factory=list)

    @property
    def consistent(self) -> bool:
        return not (self.missing_bytes or self.orphan_objects or self.stale_in_flight)


IN_FLIGHT = {"RESERVED", "UPLOADING", "VALIDATING"}
EXPECT_BYTES = {"AVAILABLE", "QUARANTINED", "RETIRED", "DELETE_ELIGIBLE"}


def compare(
    rows: Iterable[dict[str, Any]],
    objects: Iterable[tuple[str, str]],
    *,
    now: datetime | None = None,
    stale_after: timedelta = timedelta(hours=1),
) -> ConsistencyReport:
    """Pure comparison of registry rows with (bucket, key) pairs found in storage."""
    now = now or datetime.now(UTC)
    present = set(objects)
    known: set[tuple[str, str]] = set()
    report = ConsistencyReport()
    for row in rows:
        location = (str(row["bucket"]), str(row["object_key"]))
        known.add(location)
        label = f"{row['artifact_id']} v{row['version']} {row['lifecycle_status']} {location[0]}/{location[1]}"
        if row["lifecycle_status"] in EXPECT_BYTES and location not in present:
            report.missing_bytes.append(label)
        if (
            row["lifecycle_status"] in IN_FLIGHT
            and now - row["updated_at"] > stale_after
        ):
            report.stale_in_flight.append(label)
    report.orphan_objects = sorted(f"{b}/{k}" for (b, k) in present - known)
    return report


def check_consistency(
    registry: Registry,
    iter_keys: Callable[[str, str], Iterable[str]],
    *,
    stale_after: timedelta = timedelta(hours=1),
) -> ConsistencyReport:
    """Read-only sweep over all artifact buckets; reports, never repairs."""
    objects = [
        (bucket, key) for bucket in BUCKETS.values() for key in iter_keys(bucket, "v1/")
    ]
    return compare(registry.rows(), objects, stale_after=stale_after)
