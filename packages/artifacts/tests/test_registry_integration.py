"""Artifact registry against REAL PostgreSQL and SeaweedFS (WP-OBJ-001, TEST-OBJ-001-005).

A disposable database with two independent login roles (migration owner and
runtime) is created on the admin DSN of the infra profile and dropped afterwards.
Opt-in is explicit (CAP_ARTIFACT_TEST_DISPOSABLE=1) because the fixture creates
roles and a database. Missing infrastructure fails, it never skips.
"""

from __future__ import annotations

import os
import secrets
import threading
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import psycopg
import pytest
from cap_artifacts import (
    ArtifactReference,
    ArtifactStore,
    IntegrityError,
    OverwriteError,
    S3Client,
    StoreConfig,
)
from cap_artifacts.registry import (
    DuplicateVersionError,
    Registry,
    RegistryError,
    check_consistency,
    migrate,
)
from psycopg import sql
from psycopg.conninfo import make_conninfo

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class Database:
    admin_dsn: str
    migration_dsn: str
    runtime_dsn: str
    runtime_role: str


@pytest.fixture(scope="module")
def database() -> Iterator[Database]:
    admin_dsn = os.environ.get("CAP_PG_DSN")
    if not admin_dsn or os.environ.get("CAP_ARTIFACT_TEST_DISPOSABLE") != "1":
        pytest.fail(
            "CAP_PG_DSN (infra profile) and CAP_ARTIFACT_TEST_DISPOSABLE=1 are required"
        )
    name = "artifact_test_" + uuid.uuid4().hex[:12]
    migration_role, runtime_role = name + "_migration", name + "_runtime"
    passwords = {
        migration_role: secrets.token_urlsafe(24),
        runtime_role: secrets.token_urlsafe(24),
    }
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        try:
            for role, password in passwords.items():
                admin.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                        "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                    ).format(sql.Identifier(role), sql.Literal(password))
                )
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
            admin.execute(
                sql.SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                    sql.Identifier(name), sql.Identifier(migration_role)
                )
            )
            yield Database(
                admin_dsn=make_conninfo(admin_dsn, dbname=name),
                migration_dsn=make_conninfo(
                    admin_dsn,
                    dbname=name,
                    user=migration_role,
                    password=passwords[migration_role],
                ),
                runtime_dsn=make_conninfo(
                    admin_dsn,
                    dbname=name,
                    user=runtime_role,
                    password=passwords[runtime_role],
                ),
                runtime_role=runtime_role,
            )
        finally:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(name)
                )
            )
            for role in passwords:
                admin.execute(
                    sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role))
                )


@pytest.fixture(scope="module")
def registry(database: Database) -> Iterator[Registry]:
    assert migrate(database.migration_dsn, database.runtime_role) is True
    result = Registry.connect(database.runtime_dsn)
    yield result
    result.close()


@pytest.fixture(scope="module")
def store(registry: Registry) -> Iterator[ArtifactStore]:
    if not os.environ.get("CAP_S3_ENDPOINT"):
        pytest.fail("CAP_S3_ENDPOINT not set: start the infra profile")
    admin = S3Client(StoreConfig.from_env(role="admin"))
    ArtifactStore(admin).ensure_buckets()  # bucket creation needs the admin identity
    admin.close()
    client = S3Client(StoreConfig.from_env())
    result = ArtifactStore(client, registry=registry)
    yield result
    client.close()


def put(store: ArtifactStore, data: bytes, **extra: object) -> ArtifactReference:
    fields: dict[str, object] = {
        "artifact_type": "inspection_image",
        "artifact_class": "OPERATIONAL_EVIDENCE",
        "retention_class": "RC-B",
        "content_type": "application/octet-stream",
        "format_version": "raw/1",
        "logical_owner": "vision-service",
        "producer": {"service": "artifact-integration-test", "version": "0.1.0"},
        "classification": "INTERNAL",
    }
    fields.update(extra)
    return store.store(data, **fields)  # type: ignore[arg-type]


def test_migration_replay_is_verified(database: Database, registry: Registry) -> None:
    assert migrate(database.migration_dsn, database.runtime_role) is False
    other = database.runtime_role + "_other"
    with psycopg.connect(database.admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(other)))
        try:
            with pytest.raises(RegistryError, match="ledger/version/checksum mismatch"):
                migrate(database.migration_dsn, other)
        finally:
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(other)))


def test_runtime_cannot_delete_or_change_the_schema(registry: Registry) -> None:
    for statement in (
        "DELETE FROM artifact.artifact_version",
        "DROP TABLE artifact.artifact_version",
        "CREATE TABLE artifact.intruder (x int)",
        "DELETE FROM artifact.lifecycle_transition",
    ):
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            registry.conn.execute(statement)


def test_store_records_the_lifecycle(store: ArtifactStore, registry: Registry) -> None:
    ref = put(store, b"registered bytes")
    current = registry.get(ref.artifact_id, 1)
    assert current is not None and current.lifecycle_status == "AVAILABLE"
    assert store.read(ref) == b"registered bytes"


def test_database_refuses_illegal_transitions_and_content_changes(
    store: ArtifactStore, registry: Registry
) -> None:
    ref = put(store, b"immutable")
    with pytest.raises(psycopg.errors.CheckViolation, match="not allowed"):
        registry.conn.execute(
            "UPDATE artifact.artifact_version SET lifecycle_status = 'UPLOADING', "
            "reference = jsonb_set(reference, '{lifecycle_status}', '\"UPLOADING\"') "
            "WHERE artifact_id = %s",
            (ref.artifact_id,),
        )
    with pytest.raises(psycopg.errors.CheckViolation, match="immutable"):
        registry.conn.execute(
            "UPDATE artifact.artifact_version SET checksum_value = repeat('0', 64) WHERE artifact_id = %s",
            (ref.artifact_id,),
        )


def test_quarantine_in_the_registry_stops_reads(
    store: ArtifactStore, registry: Registry
) -> None:
    ref = put(store, b"suspect")
    registry.transition(ref, "QUARANTINED")
    with pytest.raises(IntegrityError, match="consumers use only AVAILABLE"):
        store.read(ref)


def test_concurrent_writers_of_one_version_get_exactly_one_success(
    database: Database, store: ArtifactStore
) -> None:
    artifact_id = str(uuid.uuid4())
    outcomes: list[str] = []
    barrier = threading.Barrier(4)

    def writer(n: int) -> None:
        reg = Registry.connect(database.runtime_dsn)
        own = ArtifactStore(store.client, registry=reg)
        barrier.wait()
        try:
            put(own, f"writer {n}".encode(), artifact_id=artifact_id)
            outcomes.append("stored")
        except OverwriteError:
            outcomes.append("refused")
        finally:
            reg.close()

    threads = [threading.Thread(target=writer, args=(n,)) for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(outcomes) == ["refused", "refused", "refused", "stored"]


def test_duplicate_reservation_is_a_registry_error(store: ArtifactStore) -> None:
    first = put(store, b"first")
    with pytest.raises(DuplicateVersionError):
        put(store, b"again", artifact_id=first.artifact_id)


def test_consistency_sweep_reports_missing_bytes_and_orphans(
    store: ArtifactStore, registry: Registry
) -> None:
    gone = put(store, b"bytes that will vanish")
    storage = gone.data["storage"]
    store.client.delete_object(storage["bucket"], storage["key"])
    stray = f"v1/inspection_image/00/{uuid.uuid4()}/v1/{uuid.uuid4()}"
    store.client.put_object(
        "cap-artifacts-rc-c",
        stray,
        b"no metadata",
        "application/octet-stream",
        "0" * 64,
    )
    report = check_consistency(registry, store.client.iter_keys)
    assert any(storage["key"] in m for m in report.missing_bytes)
    assert f"cap-artifacts-rc-c/{stray}" in report.orphan_objects
    store.client.delete_object("cap-artifacts-rc-c", stray)
