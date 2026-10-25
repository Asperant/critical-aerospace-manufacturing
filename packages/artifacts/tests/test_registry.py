"""Registry rules without a database (WP-OBJ-001, TEST-OBJ-001-004).

The store's use of a registry is driven through an in-memory registry that
enforces the same rules as the SQL table (write-once key, compare-and-set
lifecycle); the SQL itself is exercised against REAL PostgreSQL in
test_registry_integration.py. The consistency comparison is a pure function.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import resources

import httpx
import pytest
from cap_artifacts import (
    ArtifactReference,
    ArtifactStore,
    Credentials,
    IntegrityError,
    MissingObjectError,
    OverwriteError,
    S3Client,
    StoreConfig,
)
from cap_artifacts.registry import RUNTIME_TABLES, RegistryError, compare
from test_store import FakeS3, put

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)


class MemoryRegistry:
    def __init__(self) -> None:
        self.rows: dict[tuple[str, int], ArtifactReference] = {}
        self.history: list[str] = []

    def reserve(self, ref: ArtifactReference) -> None:
        key = (ref.artifact_id, ref.data["version"])
        if key in self.rows:
            raise OverwriteError("already registered")
        self.rows[key] = ref
        self.history.append(ref.lifecycle_status)

    def transition(self, ref: ArtifactReference, status: str) -> ArtifactReference:
        key = (ref.artifact_id, ref.data["version"])
        if self.rows[key].lifecycle_status != ref.lifecycle_status:
            raise RegistryError("stale")
        self.rows[key] = ref.with_status(status)
        self.history.append(status)
        return self.rows[key]

    def get(self, artifact_id: str, version: int) -> ArtifactReference | None:
        return self.rows.get((artifact_id, version))


@pytest.fixture
def s3() -> FakeS3:
    return FakeS3()


@pytest.fixture
def registry() -> MemoryRegistry:
    return MemoryRegistry()


@pytest.fixture
def store(s3: FakeS3, registry: MemoryRegistry) -> ArtifactStore:
    config = StoreConfig("http://s3.test:8333", Credentials("cap-test", "secret-value"))
    result = ArtifactStore(
        S3Client(config, transport=httpx.MockTransport(s3)), registry=registry
    )
    result.ensure_buckets()
    return result


def test_lifecycle_is_recorded_in_the_registry(
    store: ArtifactStore, registry: MemoryRegistry
) -> None:
    ref = put(store)
    assert registry.history == ["RESERVED", "UPLOADING", "VALIDATING", "AVAILABLE"]
    assert registry.get(ref.artifact_id, 1) == ref


def test_registry_refuses_a_second_reservation_before_any_upload(
    store: ArtifactStore, s3: FakeS3
) -> None:
    first = put(store)
    puts = sum(r.method == "PUT" for r in s3.requests)
    with pytest.raises(OverwriteError):
        put(store, b"other", artifact_id=first.artifact_id)
    assert sum(r.method == "PUT" for r in s3.requests) == puts


def test_failed_verification_is_recorded(
    store: ArtifactStore, s3: FakeS3, registry: MemoryRegistry
) -> None:
    s3.corrupt_reads = True
    with pytest.raises(IntegrityError):
        put(store)
    assert registry.history[-1] == "FAILED"
    assert s3.objects == {}


def test_registry_status_wins_over_a_stale_reference(
    store: ArtifactStore, registry: MemoryRegistry
) -> None:
    ref = put(store)
    registry.transition(ref, "QUARANTINED")
    with pytest.raises(IntegrityError, match="consumers use only AVAILABLE"):
        store.read(ref)  # the caller still holds the AVAILABLE copy


def test_unregistered_reference_is_not_read(
    store: ArtifactStore, registry: MemoryRegistry
) -> None:
    ref = put(store)
    registry.rows.clear()
    with pytest.raises(MissingObjectError, match="not registered"):
        store.read(ref)


def row(status: str, key: str, age: timedelta = timedelta()) -> dict[str, object]:
    return {
        "artifact_id": "a",
        "version": 1,
        "bucket": "cap-artifacts-rc-b",
        "object_key": key,
        "lifecycle_status": status,
        "updated_at": NOW - age,
    }


def test_compare_finds_missing_bytes_orphans_and_stale_reservations() -> None:
    rows = [
        row("AVAILABLE", "k1"),
        row("AVAILABLE", "k2"),
        row("DELETED", "k3"),
        row("UPLOADING", "k4", timedelta(hours=2)),
        row("RESERVED", "k5", timedelta(minutes=5)),
    ]
    objects = [("cap-artifacts-rc-b", "k1"), ("cap-artifacts-rc-b", "stray")]
    report = compare(rows, objects, now=NOW)
    assert [m.split()[-1] for m in report.missing_bytes] == ["cap-artifacts-rc-b/k2"]
    assert report.orphan_objects == ["cap-artifacts-rc-b/stray"]
    assert [m.split()[-1] for m in report.stale_in_flight] == ["cap-artifacts-rc-b/k4"]
    assert not report.consistent
    assert compare(
        [row("AVAILABLE", "k1")], [("cap-artifacts-rc-b", "k1")], now=NOW
    ).consistent


def test_runtime_privileges_exclude_delete_and_ddl() -> None:
    assert "DELETE" not in " ".join(RUNTIME_TABLES.values())
    sql = (
        resources.files("cap_artifacts")
        .joinpath("migrations/0001_registry.sql")
        .read_text("utf-8")
    )
    assert "PRIMARY KEY (artifact_id, version)" in sql
    assert "BEFORE INSERT OR UPDATE ON artifact.artifact_version" in sql
    assert (
        "GRANT" not in sql
    )  # grants are issued by migrate() for the named runtime role
