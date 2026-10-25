"""Artifact store against REAL SeaweedFS (WP-OBJ-001, TEST-OBJ-001-003).

Runs in t1-integration after `infra/compose/stack.sh up infra`, with the
environment from `stack.sh env`. Missing infrastructure fails, it never skips.
Each test uses fresh artifact identities, so runs are independent.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from cap_artifacts import (
    ArtifactReference,
    ArtifactStore,
    IntegrityError,
    MissingObjectError,
    OverwriteError,
    S3Client,
    StoreConfig,
    validate,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def store() -> Iterator[ArtifactStore]:
    if not os.environ.get("CAP_S3_ENDPOINT"):
        pytest.fail(
            "CAP_S3_ENDPOINT not set: start the infra profile (infra/compose/stack.sh up infra)"
        )
    client = S3Client(StoreConfig.from_env())
    result = ArtifactStore(client)
    result.ensure_buckets()
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


def test_buckets_exist_and_creation_is_idempotent(store: ArtifactStore) -> None:
    assert store.ensure_buckets() == store.ensure_buckets()


def test_round_trip_of_one_mebibyte(store: ArtifactStore) -> None:
    data = os.urandom(1024 * 1024)
    ref = put(store, data)
    assert ref.lifecycle_status == "AVAILABLE"
    assert validate(ref.to_dict()) == []
    assert store.read(ref) == data
    storage = ref.data["storage"]
    head = store.client.head_object(storage["bucket"], storage["key"])
    assert head is not None
    assert head.get("x-amz-meta-cap-sha256") == ref.data["checksum"]["value"]


def test_tampered_bytes_are_refused(store: ArtifactStore) -> None:
    ref = put(store, b"original evidence")
    storage = ref.data["storage"]
    store.client.put_object(
        storage["bucket"],
        storage["key"],
        b"tampered evidence",
        "application/octet-stream",
        "0" * 64,
    )
    with pytest.raises(IntegrityError):
        store.read(ref)


def test_missing_bytes_are_detected_not_silent(store: ArtifactStore) -> None:
    ref = put(store, b"soon gone")
    storage = ref.data["storage"]
    store.client.delete_object(storage["bucket"], storage["key"])
    assert not store.exists(ref)
    with pytest.raises(MissingObjectError):
        store.read(ref)


def test_a_version_is_written_once(store: ArtifactStore) -> None:
    first = put(store, b"version one")
    with pytest.raises(OverwriteError):
        put(store, b"version one again", artifact_id=first.artifact_id)
    second = put(store, b"version two", artifact_id=first.artifact_id, version=2)
    assert store.read(first) == b"version one"
    assert store.read(second) == b"version two"


def test_each_retention_class_has_its_bucket(store: ArtifactStore) -> None:
    staged = put(
        store, b"scratch", artifact_class="TEMPORARY_STAGING", retention_class="RC-D"
    )
    rebuilt = put(
        store,
        b"projection",
        artifact_class="DERIVED_REBUILDABLE",
        retention_class="RC-C",
    )
    assert staged.data["storage"]["bucket"] == "cap-artifacts-rc-d"
    assert rebuilt.data["storage"]["bucket"] == "cap-artifacts-rc-c"
    assert store.read(staged) == b"scratch"
