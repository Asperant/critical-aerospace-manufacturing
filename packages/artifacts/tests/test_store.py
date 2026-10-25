"""Artifact store against a stubbed S3 endpoint (WP-OBJ-001, TEST-OBJ-001-002).

The stub is an in-memory S3 (httpx.MockTransport) that also records requests, so
signing, the write-once rule and every failure path can be driven exactly.
The same behaviour against REAL SeaweedFS is in test_store_integration.py.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

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
    StoreError,
    validate,
)
from cap_artifacts.sigv4 import EMPTY_SHA256, sign

AUTH = re.compile(
    r"^AWS4-HMAC-SHA256 Credential=cap-test/\d{8}/us-east-1/s3/aws4_request, "
    r"SignedHeaders=[a-z0-9;-]+, Signature=[0-9a-f]{64}$"
)


class FakeS3:
    """Path-style S3 subset: bucket PUT, object PUT/GET/HEAD/DELETE, ListObjectsV2."""

    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}
        self.requests: list[httpx.Request] = []
        self.corrupt_reads = False
        self.fail_with: int | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        assert AUTH.match(request.headers["authorization"]), request.headers[
            "authorization"
        ]
        if self.fail_with:
            return httpx.Response(
                self.fail_with, content=b"<Error><Code>InternalError</Code></Error>"
            )
        parts = request.url.path.lstrip("/").split("/", 1)
        bucket, key = parts[0], (parts[1] if len(parts) > 1 else "")
        if not key:
            if request.method == "PUT":
                if bucket in self.buckets:
                    return httpx.Response(
                        409,
                        content=b"<Error><Code>BucketAlreadyOwnedByYou</Code></Error>",
                    )
                self.buckets.add(bucket)
                return httpx.Response(200)
            prefix = request.url.params.get("prefix", "")
            keys = sorted(
                k for (b, k) in self.objects if b == bucket and k.startswith(prefix)
            )
            body = "".join(f"<Contents><Key>{k}</Key></Contents>" for k in keys)
            return httpx.Response(
                200, content=f"<ListBucketResult>{body}</ListBucketResult>".encode()
            )
        if bucket not in self.buckets:
            return httpx.Response(
                404, content=b"<Error><Code>NoSuchBucket</Code></Error>"
            )
        if request.method == "PUT":
            assert (
                request.headers["x-amz-content-sha256"]
                == hashlib.sha256(request.content).hexdigest()
            )
            self.objects[(bucket, key)] = request.content
            return httpx.Response(200)
        if (bucket, key) not in self.objects:
            return httpx.Response(404, content=b"<Error><Code>NoSuchKey</Code></Error>")
        if request.method == "DELETE":
            del self.objects[(bucket, key)]
            return httpx.Response(204)
        data = self.objects[(bucket, key)]
        if self.corrupt_reads:
            data = data[:-1] + bytes([data[-1] ^ 1])
        if request.method == "HEAD":
            return httpx.Response(200, headers={"content-length": str(len(data))})
        return httpx.Response(200, content=data)


@pytest.fixture
def s3() -> FakeS3:
    return FakeS3()


@pytest.fixture
def store(s3: FakeS3) -> ArtifactStore:
    config = StoreConfig("http://s3.test:8333", Credentials("cap-test", "secret-value"))
    result = ArtifactStore(
        S3Client(config, transport=httpx.MockTransport(s3)),
        clock=lambda: datetime(2026, 10, 25, 9, 0, tzinfo=UTC),
    )
    result.ensure_buckets()
    return result


def put(
    store: ArtifactStore, data: bytes = b"inspection bytes", **extra: Any
) -> ArtifactReference:
    fields: dict[str, Any] = {
        "artifact_type": "inspection_image",
        "artifact_class": "OPERATIONAL_EVIDENCE",
        "retention_class": "RC-B",
        "content_type": "image/png",
        "format_version": "png/1",
        "logical_owner": "vision-service",
        "producer": {"service": "manufacturing-simulator", "version": "0.1.0"},
        "classification": "INTERNAL",
        "provenance": {
            "source_artifacts": [],
            "source_refs": ["inspection_request:IR-1"],
        },
    }
    fields.update(extra)
    return store.store(data, **fields)


def test_store_writes_verifies_and_returns_available_reference(
    store: ArtifactStore, s3: FakeS3
) -> None:
    ref = put(store)
    assert ref.lifecycle_status == "AVAILABLE"
    assert validate(ref.to_dict()) == []
    storage = ref.data["storage"]
    assert storage["bucket"] == "cap-artifacts-rc-b"
    assert s3.objects[(storage["bucket"], storage["key"])] == b"inspection bytes"
    assert store.read(ref) == b"inspection bytes"
    assert store.exists(ref)
    methods = [r.method for r in s3.requests[3:]]
    assert methods == [
        "GET",
        "PUT",
        "GET",
        "GET",
        "HEAD",
    ]  # list, put, verify, read, head


def test_buckets_are_created_idempotently(store: ArtifactStore, s3: FakeS3) -> None:
    assert store.ensure_buckets() == [
        "cap-artifacts-rc-b",
        "cap-artifacts-rc-c",
        "cap-artifacts-rc-d",
    ]
    assert s3.buckets == set(store.ensure_buckets())


def test_a_version_is_written_once(store: ArtifactStore) -> None:
    first = put(store)
    with pytest.raises(OverwriteError, match="new bytes need a new version"):
        put(store, b"other bytes", artifact_id=first.artifact_id)
    second = put(store, b"other bytes", artifact_id=first.artifact_id, version=2)
    assert second.data["storage"]["key"] != first.data["storage"]["key"]
    assert store.read(first) == b"inspection bytes"


def test_corrupted_readback_fails_and_removes_the_object(
    store: ArtifactStore, s3: FakeS3
) -> None:
    s3.corrupt_reads = True
    with pytest.raises(IntegrityError, match="checksum mismatch"):
        put(store)
    assert s3.objects == {}


def test_corrupted_bytes_are_never_handed_out(store: ArtifactStore, s3: FakeS3) -> None:
    ref = put(store)
    s3.corrupt_reads = True
    with pytest.raises(IntegrityError):
        store.read(ref)


def test_missing_bytes_are_detected(store: ArtifactStore, s3: FakeS3) -> None:
    ref = put(store)
    s3.objects.clear()
    with pytest.raises(MissingObjectError):
        store.read(ref)
    assert not store.exists(ref)


def test_non_available_reference_is_not_read(store: ArtifactStore) -> None:
    ref = put(store).with_status("QUARANTINED")
    with pytest.raises(IntegrityError, match="consumers use only AVAILABLE"):
        store.read(ref)


def test_invalid_metadata_is_refused_before_any_upload(
    store: ArtifactStore, s3: FakeS3
) -> None:
    before = len(s3.requests)
    with pytest.raises(ValueError):
        put(store, retention_class="RC-A")
    with pytest.raises(ValueError):
        put(store, artifact_class="TEMPORARY_STAGING")  # must be RC-D
    assert len(s3.requests) == before


def test_store_errors_are_explicit(store: ArtifactStore, s3: FakeS3) -> None:
    s3.fail_with = 500
    with pytest.raises(StoreError, match="HTTP 500 InternalError"):
        put(store)


def test_unreachable_store_is_a_store_error() -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = S3Client(
        StoreConfig("http://s3.test:1", Credentials("cap-test")),
        transport=httpx.MockTransport(refuse),
    )
    with pytest.raises(StoreError, match="unreachable"):
        client.create_bucket("cap-artifacts-rc-b")


def test_config_from_env_per_role_and_secret_never_printed() -> None:
    env = {
        "CAP_S3_ENDPOINT": "http://127.0.0.1:28333/",
        "CAP_S3_ACCESS_KEY": "cap-artifacts-writer",
        "CAP_S3_SECRET_KEY": "s3cr3t-writer",
        "CAP_S3_ADMIN_ACCESS_KEY": "cap-artifacts-admin",
        "CAP_S3_ADMIN_SECRET_KEY": "s3cr3t-admin",
        "CAP_S3_READER_ACCESS_KEY": "cap-artifacts-reader",
        "CAP_S3_READER_SECRET_KEY": "s3cr3t-reader",
    }
    writer = StoreConfig.from_env(env)
    assert writer.endpoint == "http://127.0.0.1:28333"
    assert writer.credentials.access_key == "cap-artifacts-writer"
    assert (
        StoreConfig.from_env(env, role="admin").credentials.access_key
        == "cap-artifacts-admin"
    )
    assert (
        StoreConfig.from_env(env, role="reader").credentials.secret_key
        == "s3cr3t-reader"
    )
    assert "s3cr3t" not in repr(writer)
    with pytest.raises(StoreError, match="CAP_S3_ENDPOINT"):
        StoreConfig.from_env({})
    with pytest.raises(StoreError, match="CAP_S3_READER_ACCESS_KEY"):
        StoreConfig.from_env({"CAP_S3_ENDPOINT": "http://x"}, role="reader")
    with pytest.raises(StoreError, match="unknown storage role"):
        StoreConfig.from_env(env, role="root")


AWS = Credentials("AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
WHEN = datetime(2013, 5, 24, tzinfo=UTC)


@pytest.mark.parametrize(
    ("method", "path", "query", "headers", "payload", "signature"),
    [
        (
            "GET", "/test.txt", {}, {"Range": "bytes=0-9"}, b"",
            "f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41",
        ),
        (
            "PUT", "/test$file.text", {},
            {"Date": "Fri, 24 May 2013 00:00:00 GMT", "x-amz-storage-class": "REDUCED_REDUNDANCY"},
            b"Welcome to Amazon S3.",
            "98ad721746da40c64f1a55b78f14c238d841ea1380cd77a1b5971af0ece108bd",
        ),
        (
            "GET", "/", {"max-keys": "2", "prefix": "J"}, {}, b"",
            "34b48302e7b5fa45bde8084f4b7868a86f0a534bc59db6670ed5711ef69dc6f7",
        ),
    ],
)  # fmt: skip
def test_sigv4_matches_the_published_aws_examples(
    method: str,
    path: str,
    query: dict[str, str],
    headers: dict[str, str],
    payload: bytes,
    signature: str,
) -> None:
    signed = sign(
        method=method,
        host="examplebucket.s3.amazonaws.com",
        path=path,
        query=query,
        headers=headers,
        payload_sha256=hashlib.sha256(payload).hexdigest() if payload else EMPTY_SHA256,
        credentials=AWS,
        region="us-east-1",
        now=WHEN,
    )
    assert signed["authorization"].endswith("Signature=" + signature)
