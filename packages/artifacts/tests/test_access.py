"""Scoped read capabilities without a live store (WP-OBJ-001, TEST-OBJ-001-006).

Issuance rules are driven against the stubbed S3 and in-memory registry; the
same capabilities against REAL SeaweedFS identities are in
test_access_integration.py.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cap_artifacts import (
    ArtifactReference,
    ArtifactStore,
    Credentials,
    S3Client,
    StoreConfig,
)
from cap_artifacts.access import MAX_TTL, AccessDenied, AccessIssuer
from cap_artifacts.sigv4 import presign
from test_registry import MemoryRegistry
from test_store import FakeS3, put

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
READER = StoreConfig(
    "http://127.0.0.1:28333", Credentials("cap-artifacts-reader", "reader-secret")
)


@pytest.fixture
def registry() -> MemoryRegistry:
    return MemoryRegistry()


@pytest.fixture
def store(registry: MemoryRegistry) -> ArtifactStore:
    config = StoreConfig("http://s3.test:8333", Credentials("cap-test", "secret-value"))
    result = ArtifactStore(
        S3Client(config, transport=httpx.MockTransport(FakeS3())), registry=registry
    )
    result.ensure_buckets()
    return result


def issuer(store: ArtifactStore, allowed: set[str]) -> AccessIssuer:
    return AccessIssuer(
        store, READER, lambda actor, ref: actor in allowed, clock=lambda: NOW
    )


def test_capability_is_one_get_of_one_object_signed_by_the_reader(
    store: ArtifactStore,
) -> None:
    ref = put(store)
    cap = issuer(store, {"operator-7"}).issue(ref, "operator-7")
    url = urlsplit(cap.url)
    query = {k: v[0] for k, v in parse_qs(url.query).items()}
    storage = ref.data["storage"]
    assert url.path == f"/{storage['bucket']}/{storage['key']}"
    assert query["X-Amz-Credential"].startswith("cap-artifacts-reader/20261025/")
    assert query["X-Amz-Expires"] == "300"
    assert query["X-Amz-SignedHeaders"] == "host"
    assert cap.expires_at == NOW + timedelta(minutes=5)
    assert "reader-secret" not in cap.url
    assert "url=<redacted>" in repr(cap) and "X-Amz-Signature" not in repr(cap)


def test_unauthorized_actor_is_denied(store: ArtifactStore) -> None:
    ref = put(store)
    with pytest.raises(AccessDenied, match="may not read"):
        issuer(store, {"someone-else"}).issue(ref, "operator-7")
    with pytest.raises(AccessDenied, match="actor identity"):
        issuer(store, {""}).issue(ref, " ")


def test_quarantined_artifact_gets_no_capability(
    store: ArtifactStore, registry: MemoryRegistry
) -> None:
    ref = put(store)
    registry.transition(ref, "QUARANTINED")
    with pytest.raises(AccessDenied, match="only AVAILABLE"):
        issuer(store, {"operator-7"}).issue(ref, "operator-7")


@pytest.mark.parametrize(
    "ttl", [timedelta(0), MAX_TTL + timedelta(seconds=1), timedelta(days=1)]
)
def test_capability_lifetime_is_bounded(store: ArtifactStore, ttl: timedelta) -> None:
    ref: ArtifactReference = put(store)
    with pytest.raises(AccessDenied, match="lifetime"):
        issuer(store, {"operator-7"}).issue(ref, "operator-7", ttl=ttl)


def test_presign_matches_the_published_aws_example() -> None:
    query = presign(
        method="GET",
        host="examplebucket.s3.amazonaws.com",
        path="/test.txt",
        credentials=Credentials(
            "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        ),
        region="us-east-1",
        now=datetime(2013, 5, 24, tzinfo=UTC),
        expires_s=86400,
    )
    assert (
        query["X-Amz-Signature"]
        == "aeeed9bbccd4d02ee5c0109b86d86835f995330da4c265957d157751f604d404"
    )


def test_bucket_names_match_the_infra_identities() -> None:
    from pathlib import Path

    from cap_artifacts import BUCKETS

    script = (Path(__file__).resolve().parents[3] / "infra/compose/stack.sh").read_text(
        "utf-8"
    )
    line = next(
        line for line in script.splitlines() if line.startswith("ARTIFACT_BUCKETS=")
    )
    assert sorted(line.split("(")[1].rstrip(")").split()) == sorted(BUCKETS.values())
