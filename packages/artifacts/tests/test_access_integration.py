"""Storage identities and read capabilities against REAL SeaweedFS (WP-OBJ-001, TEST-OBJ-001-007).

The infra profile defines three S3 identities (stack.sh): admin creates buckets,
writer reads/lists/writes artifacts, reader only reads. Anonymous access is
denied. Read capabilities are pre-signed by the reader.
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from datetime import timedelta
from urllib.parse import urlsplit, urlunsplit

import httpx
import pytest
from cap_artifacts import ArtifactReference, ArtifactStore, S3Client, StoreConfig
from cap_artifacts.access import AccessIssuer

pytestmark = pytest.mark.integration


def config(role: str) -> StoreConfig:
    if not os.environ.get("CAP_S3_ENDPOINT"):
        pytest.fail(
            "CAP_S3_ENDPOINT not set: start the infra profile (stack.sh up infra)"
        )
    return StoreConfig.from_env(role=role)


@pytest.fixture(scope="module")
def store() -> Iterator[ArtifactStore]:
    admin = S3Client(config("admin"))
    ArtifactStore(admin).ensure_buckets()
    admin.close()
    client = S3Client(config("writer"))
    yield ArtifactStore(client)
    client.close()


@pytest.fixture(scope="module")
def ref(store: ArtifactStore) -> ArtifactReference:
    return store.store(
        b"inspection image bytes",
        artifact_type="inspection_image",
        artifact_class="OPERATIONAL_EVIDENCE",
        retention_class="RC-B",
        content_type="application/octet-stream",
        format_version="raw/1",
        logical_owner="vision-service",
        producer={"service": "artifact-integration-test", "version": "0.1.0"},
        classification="INTERNAL",
    )


def object_url(ref: ArtifactReference) -> str:
    storage = ref.data["storage"]
    return f"{os.environ['CAP_S3_ENDPOINT']}/{storage['bucket']}/{storage['key']}"


def test_anonymous_access_is_denied(ref: ArtifactReference) -> None:
    assert httpx.get(object_url(ref)).status_code == 403
    assert httpx.put(object_url(ref) + "-anon", content=b"x").status_code == 403


def test_reader_cannot_write_and_writer_cannot_create_buckets(
    ref: ArtifactReference,
) -> None:
    reader = S3Client(config("reader"))
    storage = ref.data["storage"]
    response = reader.request(
        "PUT", storage["bucket"], storage["key"] + "-by-reader", body=b"x"
    )
    assert response.status_code == 403
    assert (
        reader.get_object(storage["bucket"], storage["key"])
        == b"inspection image bytes"
    )
    writer = S3Client(config("writer"))
    assert writer.request("PUT", "cap-artifacts-not-allowed").status_code == 403
    reader.close()
    writer.close()


def issue(
    store: ArtifactStore, ref: ArtifactReference, ttl: timedelta = timedelta(minutes=5)
) -> str:
    issuer = AccessIssuer(
        store, config("reader"), lambda actor, _: actor == "operator-7"
    )
    return issuer.issue(ref, "operator-7", ttl=ttl).url


def test_read_capability_reads_exactly_that_object(
    store: ArtifactStore, ref: ArtifactReference
) -> None:
    url = issue(store, ref)
    response = httpx.get(url)
    assert response.status_code == 200
    assert response.content == b"inspection image bytes"


def test_read_capability_cannot_be_reused_for_anything_else(
    store: ArtifactStore, ref: ArtifactReference
) -> None:
    url = issue(store, ref)
    parts = urlsplit(url)
    other = store.store(
        b"another artifact",
        artifact_type="inspection_image",
        artifact_class="OPERATIONAL_EVIDENCE",
        retention_class="RC-B",
        content_type="application/octet-stream",
        format_version="raw/1",
        logical_owner="vision-service",
        producer={"service": "artifact-integration-test", "version": "0.1.0"},
        classification="INTERNAL",
    )
    other_path = "/" + "/".join(
        [other.data["storage"]["bucket"], other.data["storage"]["key"]]
    )
    assert httpx.get(urlunsplit(parts._replace(path=other_path))).status_code == 403
    tampered = url[:-1] + ("0" if url[-1] != "0" else "1")
    assert httpx.get(tampered).status_code == 403
    assert httpx.put(url, content=b"overwrite attempt").status_code == 403
    assert httpx.delete(url).status_code == 403


def test_read_capability_expires(store: ArtifactStore, ref: ArtifactReference) -> None:
    url = issue(store, ref, ttl=timedelta(seconds=1))
    time.sleep(3)
    assert httpx.get(url).status_code == 403
