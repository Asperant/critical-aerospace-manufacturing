"""Artifact store on the S3 API (SeaweedFS): write, verify, read (WP-OBJ-001).

The write path follows the 02 finalization protocol: reserve identities
(RESERVED) -> upload the bytes to a fresh object (UPLOADING) -> read them back and
verify size and SHA-256 (VALIDATING) -> AVAILABLE. Any failure leaves no
AVAILABLE reference behind: a digest mismatch removes the object and raises.

A version is written once. If any object already exists under the version's
prefix the write is refused; new bytes need a new version. Reads hand out bytes
only for AVAILABLE references and only after verifying them. Relational metadata,
atomic reservation and cross-store consistency arrive in slice 3; scoped access
and storage identities in slice 4.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol, cast
from urllib.parse import urlsplit

import httpx

from cap_artifacts.conventions import (
    BUCKETS,
    bucket_for,
    new_id,
    object_key,
    version_prefix,
)
from cap_artifacts.errors import MissingObjectError, OverwriteError, StoreError
from cap_artifacts.integrity import IntegrityError, digest_bytes
from cap_artifacts.reference import SCHEMA_ID, ArtifactReference
from cap_artifacts.sigv4 import EMPTY_SHA256, Credentials, sign

S3_NS = "{http://s3.amazonaws.com/doc/2006-03-01/}"
CHECKSUM_META = "x-amz-meta-cap-sha256"


@dataclass(frozen=True)
class StoreConfig:
    endpoint: str
    credentials: Credentials
    region: str = "us-east-1"
    timeout_s: float = 30.0

    @classmethod
    def from_env(
        cls, env: Mapping[str, str] | None = None, role: str = "writer"
    ) -> StoreConfig:
        """Endpoint and credentials of one storage identity, as printed by
        `infra/compose/stack.sh env`: CAP_S3_ENDPOINT, and CAP_S3_ACCESS_KEY /
        CAP_S3_SECRET_KEY (writer), CAP_S3_ADMIN_* (admin: creates buckets) or
        CAP_S3_READER_* (reader: signs read capabilities). No default secret."""
        values = os.environ if env is None else env
        endpoint = values.get("CAP_S3_ENDPOINT", "")
        if not endpoint:
            raise StoreError("CAP_S3_ENDPOINT is not set (infra/compose/stack.sh env)")
        prefix = {
            "writer": "CAP_S3_",
            "admin": "CAP_S3_ADMIN_",
            "reader": "CAP_S3_READER_",
        }.get(role)
        if prefix is None:
            raise StoreError(f"unknown storage role {role!r}")
        access, secret = (
            values.get(prefix + "ACCESS_KEY", ""),
            values.get(prefix + "SECRET_KEY", ""),
        )
        if not access or not secret:
            raise StoreError(
                f"{prefix}ACCESS_KEY and {prefix}SECRET_KEY are not set (stack.sh env)"
            )
        return cls(
            endpoint=endpoint.rstrip("/"),
            credentials=Credentials(access, secret),
            region=values.get("CAP_S3_REGION", "us-east-1"),
        )


def _texts(root: ET.Element, path: str) -> list[str]:
    """Text of `path` under an S3 XML response, with or without the S3 namespace."""
    namespaced = S3_NS + path.replace("/", "/" + S3_NS)
    nodes = root.findall(namespaced) or root.findall(path)
    return [node.text or "" for node in nodes]


class S3Client:
    """Minimal signed S3 client: path-style requests, one bucket/key at a time."""

    def __init__(
        self, config: StoreConfig, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.config = config
        self._host = urlsplit(config.endpoint).netloc
        self._http = httpx.Client(
            base_url=config.endpoint, timeout=config.timeout_s, transport=transport
        )

    def close(self) -> None:
        self._http.close()

    def request(
        self,
        method: str,
        bucket: str,
        key: str = "",
        *,
        query: Mapping[str, str] | None = None,
        body: bytes = b"",
        headers: Mapping[str, str] | None = None,
        payload_sha256: str | None = None,
    ) -> httpx.Response:
        path = f"/{bucket}" + (f"/{key}" if key else "")
        query = dict(query or {})
        signed = sign(
            method=method,
            host=self._host,
            path=path,
            query=query,
            headers=dict(headers or {}),
            payload_sha256=payload_sha256
            or (digest_bytes(body).value if body else EMPTY_SHA256),
            credentials=self.config.credentials,
            region=self.config.region,
            now=datetime.now(UTC),
        )
        try:
            return self._http.request(
                method, path, params=query, content=body, headers=signed
            )
        except httpx.HTTPError as exc:
            raise StoreError(
                f"object store unreachable: {type(exc).__name__}"
            ) from None

    @staticmethod
    def _fail(response: httpx.Response, action: str) -> StoreError:
        code = ""
        try:
            node = ET.fromstring(response.content).find("Code")
            code = (node.text or "") if node is not None else ""
        except ET.ParseError:
            pass
        return StoreError(f"{action}: HTTP {response.status_code} {code}".rstrip())

    def create_bucket(self, bucket: str) -> None:
        response = self.request("PUT", bucket)
        if response.status_code == 200:
            return
        if (
            response.status_code == 409
            and b"BucketAlreadyOwnedByYou" in response.content
        ):
            return
        if response.status_code == 409 and b"BucketAlreadyExists" in response.content:
            return
        raise self._fail(response, f"create bucket {bucket}")

    def put_object(
        self, bucket: str, key: str, data: bytes, content_type: str, sha256: str
    ) -> None:
        response = self.request(
            "PUT",
            bucket,
            key,
            body=data,
            headers={"content-type": content_type, CHECKSUM_META: sha256},
            payload_sha256=sha256,
        )
        if response.status_code != 200:
            raise self._fail(response, f"put {bucket}/{key}")

    def get_object(self, bucket: str, key: str) -> bytes:
        response = self.request("GET", bucket, key)
        if response.status_code == 404:
            raise MissingObjectError(f"no bytes at {bucket}/{key}")
        if response.status_code != 200:
            raise self._fail(response, f"get {bucket}/{key}")
        return response.content

    def head_object(self, bucket: str, key: str) -> dict[str, str] | None:
        response = self.request("HEAD", bucket, key)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise self._fail(response, f"head {bucket}/{key}")
        return {k.lower(): v for k, v in response.headers.items()}

    def delete_object(self, bucket: str, key: str) -> None:
        response = self.request("DELETE", bucket, key)
        if response.status_code not in (200, 204, 404):
            raise self._fail(response, f"delete {bucket}/{key}")

    def iter_keys(self, bucket: str, prefix: str, page: int = 1000) -> Iterator[str]:
        """Every key under `prefix` (ListObjectsV2, following continuation tokens)."""
        token = ""
        while True:
            query = {"list-type": "2", "prefix": prefix, "max-keys": str(page)}
            if token:
                query["continuation-token"] = token
            response = self.request("GET", bucket, query=query)
            if response.status_code == 404:
                return
            if response.status_code != 200:
                raise self._fail(response, f"list {bucket}/{prefix}")
            root = ET.fromstring(response.content)

            yield from _texts(root, "Contents/Key")
            truncated = _texts(root, "IsTruncated")
            token = (_texts(root, "NextContinuationToken") or [""])[0]
            if not truncated or truncated[0] != "true" or not token:
                return

    def list_keys(self, bucket: str, prefix: str) -> list[str]:
        return list(self.iter_keys(bucket, prefix))


class VersionRegistry(Protocol):
    """What the store needs from the relational registry (cap_artifacts.registry)."""

    def reserve(self, ref: ArtifactReference) -> None: ...

    def transition(self, ref: ArtifactReference, status: str) -> ArtifactReference: ...

    def get(self, artifact_id: str, version: int) -> ArtifactReference | None: ...


class ArtifactStore:
    """Write-once, verify-always artifact storage over an S3Client."""

    def __init__(
        self,
        client: S3Client,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        registry: VersionRegistry | None = None,
    ) -> None:
        self.client = client
        self.clock = clock
        self.registry = registry

    def ensure_buckets(self) -> list[str]:
        for bucket in BUCKETS.values():
            self.client.create_bucket(bucket)
        return list(BUCKETS.values())

    def store(
        self,
        data: bytes,
        *,
        artifact_type: str,
        artifact_class: str,
        retention_class: str,
        content_type: str,
        format_version: str,
        logical_owner: str,
        producer: Mapping[str, str],
        classification: str,
        context: Mapping[str, str | None] | None = None,
        provenance: Mapping[str, list[str]] | None = None,
        artifact_id: str | None = None,
        version: int = 1,
    ) -> ArtifactReference:
        """Write `data` as a new artifact version and return its AVAILABLE reference."""
        artifact_id = artifact_id or new_id()
        object_id = new_id()
        digest = digest_bytes(data)
        bucket = bucket_for(retention_class)
        key = object_key(artifact_type, artifact_id, version, object_id)
        draft: dict[str, Any] = {
            "schema": SCHEMA_ID,
            "artifact_id": artifact_id,
            "version": version,
            "artifact_type": artifact_type,
            "artifact_class": artifact_class,
            "format_version": format_version,
            "content_type": content_type,
            "size_bytes": digest.size_bytes,
            "checksum": {"algorithm": digest.algorithm, "value": digest.value},
            "logical_owner": logical_owner,
            "producer": dict(producer),
            "created_at": self.clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "context": dict(
                context
                or {"world_id": None, "simulation_run_id": None, "branch_id": None}
            ),
            "classification": classification,
            "retention_class": retention_class,
            "storage": {"bucket": bucket, "key": key, "object_id": object_id},
            "lifecycle_status": "RESERVED",
            "provenance": {
                "source_artifacts": list(
                    (provenance or {}).get("source_artifacts", [])
                ),
                "source_refs": list((provenance or {}).get("source_refs", [])),
            },
        }
        ref = ArtifactReference.from_dict(draft)  # validates before any byte moves
        if self.registry is not None:
            self.registry.reserve(ref)  # atomic: a version is registered once
        if self.client.list_keys(
            bucket, version_prefix(artifact_type, artifact_id, version)
        ):
            self._move(ref, "ABORTED")
            raise OverwriteError(
                f"artifact {artifact_id} v{version} already has bytes; new bytes need a new version"
            )
        ref = self._move(ref, "UPLOADING")
        try:
            self.client.put_object(bucket, key, data, content_type, digest.value)
        except StoreError:
            self._move(ref, "FAILED")
            raise
        ref = self._move(ref, "VALIDATING")
        try:
            ref.verify_bytes(self.client.get_object(bucket, key))
        except (IntegrityError, MissingObjectError):
            self.client.delete_object(bucket, key)
            self._move(ref, "FAILED")
            raise
        return self._move(ref, "AVAILABLE")

    def _move(self, ref: ArtifactReference, status: str) -> ArtifactReference:
        if self.registry is not None:
            return self.registry.transition(ref, status)
        return ref.with_status(status)

    def current(self, ref: ArtifactReference) -> ArtifactReference:
        """The registry's view of `ref` (its lifecycle may have moved on)."""
        if self.registry is None:
            return ref
        found = self.registry.get(ref.artifact_id, cast(int, ref.data["version"]))
        if found is None:
            raise MissingObjectError(f"artifact {ref.artifact_id} is not registered")
        if (
            found.data["storage"] != ref.data["storage"]
            or found.data["checksum"] != ref.data["checksum"]
        ):
            raise IntegrityError(
                f"reference for {ref.artifact_id} differs from the registry"
            )
        return found

    def read(self, ref: ArtifactReference) -> bytes:
        """The artifact's bytes, only if AVAILABLE (per the registry when there is
        one) and only after verification."""
        ref = self.current(ref)
        ref.require_consumable()
        storage = cast(dict[str, str], ref.data["storage"])
        data = self.client.get_object(storage["bucket"], storage["key"])
        ref.verify_bytes(data)
        return data

    def exists(self, ref: ArtifactReference) -> bool:
        storage = cast(dict[str, str], ref.data["storage"])
        return self.client.head_object(storage["bucket"], storage["key"]) is not None
