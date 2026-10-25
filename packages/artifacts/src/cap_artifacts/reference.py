"""`cap.artifact-ref/v1` — the ArtifactReference contract (IC-SHARED-001, WP-OBJ-001).

`validate()` checks a reference as plain data: every rule of the JSON Schema in
`schemas/artifact-reference.schema.json` (structure, enums, patterns) plus the
rules a schema cannot express — the storage key and bucket must follow from the
identities and the retention class, and class/retention combinations must make
sense. `ArtifactReference.from_dict()` refuses anything `validate()` rejects.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from importlib import resources
from typing import Any, cast

from cap_artifacts.conventions import (
    ARTIFACT_CLASSES,
    BUCKETS,
    CLASSIFICATIONS,
    CONSUMABLE,
    LIFECYCLE,
    TYPE_RE,
    UUID_RE,
    object_key,
    require_transition,
)
from cap_artifacts.integrity import (
    ALGORITHM,
    Digest,
    IntegrityError,
    digest_bytes,
    verify,
)

SCHEMA_ID = "cap.artifact-ref/v1"
REQUIRED = (
    "schema", "artifact_id", "version", "artifact_type", "artifact_class", "format_version",
    "content_type", "size_bytes", "checksum", "logical_owner", "producer", "created_at",
    "context", "classification", "retention_class", "storage", "lifecycle_status", "provenance",
)  # fmt: skip
SERVICE_RE = re.compile(r"^[a-z][a-z0-9-]{1,62}$")
FORMAT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/+-]{0,63}$")
CONTENT_TYPE_RE = re.compile(r"^[a-z]+/[a-z0-9][a-z0-9.+-]{0,126}$")
INSTANT_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{1,9})?Z$"
)
OPTIONAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SOURCE_REF_RE = re.compile(r"^[a-z][a-z0-9_]{1,40}:[A-Za-z0-9._:-]{1,128}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RETENTION = {"TEMPORARY_STAGING": "RC-D", "VERSIONED_RELEASE": "RC-B"}


class InvalidReferenceError(ValueError):
    """Data is not a valid `cap.artifact-ref/v1` reference."""


def schema() -> dict[str, Any]:
    text = resources.files("cap_artifacts").joinpath(
        "schemas/artifact-reference.schema.json"
    )
    return cast(dict[str, Any], json.loads(text.read_text("utf-8")))


def _obj(value: object) -> dict[str, Any] | None:
    return cast(dict[str, Any], value) if isinstance(value, dict) else None


def _exact_keys(
    errors: list[str], where: str, data: dict[str, Any], keys: tuple[str, ...]
) -> None:
    missing = [k for k in keys if k not in data]
    extra = sorted(set(data) - set(keys))
    if missing:
        errors.append(f"{where}: missing {', '.join(missing)}")
    if extra:
        errors.append(f"{where}: unexpected {', '.join(extra)}")


def _match(
    errors: list[str], where: str, value: object, pattern: re.Pattern[str]
) -> bool:
    if isinstance(value, str) and pattern.match(value):
        return True
    errors.append(f"{where}: {value!r} does not match {pattern.pattern}")
    return False


def _int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate(data: object) -> list[str]:  # noqa: C901 - one flat rule list mirrors the schema
    """Every rule violation of `data` as a reference; empty when valid."""
    ref = _obj(data)
    if ref is None:
        return ["reference must be an object"]
    errors: list[str] = []
    _exact_keys(errors, "reference", ref, REQUIRED)
    if ref.get("schema") != SCHEMA_ID:
        errors.append(f"schema: must be {SCHEMA_ID}")
    _match(errors, "artifact_id", ref.get("artifact_id"), UUID_RE)
    version = ref.get("version")
    if not _int(version) or cast(int, version) < 1:
        errors.append("version: must be an integer >= 1")
    _match(errors, "artifact_type", ref.get("artifact_type"), TYPE_RE)
    if ref.get("artifact_class") not in ARTIFACT_CLASSES:
        errors.append(
            f"artifact_class: {ref.get('artifact_class')!r} is not an 02 artifact class"
        )
    _match(errors, "format_version", ref.get("format_version"), FORMAT_RE)
    _match(errors, "content_type", ref.get("content_type"), CONTENT_TYPE_RE)
    size = ref.get("size_bytes")
    if not _int(size) or cast(int, size) < 0:
        errors.append("size_bytes: must be an integer >= 0")
    checksum = _obj(ref.get("checksum"))
    if checksum is None:
        errors.append("checksum: must be an object")
    else:
        _exact_keys(errors, "checksum", checksum, ("algorithm", "value"))
        if checksum.get("algorithm") != ALGORITHM:
            errors.append(f"checksum.algorithm: must be {ALGORITHM}")
        _match(errors, "checksum.value", checksum.get("value"), HEX64_RE)
    _match(errors, "logical_owner", ref.get("logical_owner"), SERVICE_RE)
    producer = _obj(ref.get("producer"))
    if producer is None:
        errors.append("producer: must be an object")
    else:
        _exact_keys(errors, "producer", producer, ("service", "version"))
        _match(errors, "producer.service", producer.get("service"), SERVICE_RE)
        pv = producer.get("version")
        if not isinstance(pv, str) or not 1 <= len(pv) <= 64:
            errors.append("producer.version: must be a string of 1-64 characters")
    _match(errors, "created_at", ref.get("created_at"), INSTANT_RE)
    context = _obj(ref.get("context"))
    if context is None:
        errors.append("context: must be an object")
    else:
        _exact_keys(
            errors, "context", context, ("world_id", "simulation_run_id", "branch_id")
        )
        for name in ("world_id", "simulation_run_id", "branch_id"):
            value = context.get(name)
            if value is not None:
                _match(errors, f"context.{name}", value, OPTIONAL_ID_RE)
    if ref.get("classification") not in CLASSIFICATIONS:
        errors.append(
            f"classification: {ref.get('classification')!r} is not an 02 level"
        )
    retention = ref.get("retention_class")
    if retention not in BUCKETS:
        errors.append(f"retention_class: {retention!r} is not RC-B, RC-C or RC-D")
    if ref.get("lifecycle_status") not in LIFECYCLE:
        errors.append(
            f"lifecycle_status: {ref.get('lifecycle_status')!r} is not an 02 status"
        )
    _validate_storage(errors, ref)
    _validate_provenance(errors, ref)
    required = REQUIRED_RETENTION.get(str(ref.get("artifact_class")))
    if required is not None and retention in BUCKETS and retention != required:
        errors.append(
            f"retention_class: {ref.get('artifact_class')} artifacts must be {required}"
        )
    return errors


def _validate_storage(errors: list[str], ref: dict[str, Any]) -> None:
    storage = _obj(ref.get("storage"))
    if storage is None:
        errors.append("storage: must be an object")
        return
    _exact_keys(errors, "storage", storage, ("bucket", "key", "object_id"))
    if storage.get("bucket") not in BUCKETS.values():
        errors.append(
            f"storage.bucket: {storage.get('bucket')!r} is not an artifact bucket"
        )
    elif (
        ref.get("retention_class") in BUCKETS
        and storage["bucket"] != BUCKETS[ref["retention_class"]]
    ):
        errors.append(
            f"storage.bucket: {ref['retention_class']} artifacts live in {BUCKETS[ref['retention_class']]}"
        )
    ok_object = _match(errors, "storage.object_id", storage.get("object_id"), UUID_RE)
    ids_ok = (
        ok_object
        and isinstance(ref.get("artifact_type"), str)
        and TYPE_RE.match(ref["artifact_type"])
        and isinstance(ref.get("artifact_id"), str)
        and UUID_RE.match(ref["artifact_id"])
    )
    if ids_ok:
        expected = object_key(
            ref["artifact_type"], ref["artifact_id"], storage["object_id"]
        )
        if storage.get("key") != expected:
            errors.append(
                f"storage.key: must be {expected} (derived from identities only)"
            )
    elif not isinstance(storage.get("key"), str):
        errors.append("storage.key: must be a string")


def _validate_provenance(errors: list[str], ref: dict[str, Any]) -> None:
    provenance = _obj(ref.get("provenance"))
    if provenance is None:
        errors.append("provenance: must be an object")
        return
    _exact_keys(errors, "provenance", provenance, ("source_artifacts", "source_refs"))
    for name, pattern in (
        ("source_artifacts", UUID_RE),
        ("source_refs", SOURCE_REF_RE),
    ):
        items = provenance.get(name)
        if not isinstance(items, list):
            errors.append(f"provenance.{name}: must be a list")
            continue
        values = cast(list[object], items)
        if len(values) > 64:
            errors.append(f"provenance.{name}: at most 64 entries")
        if len({json.dumps(v, sort_keys=True) for v in values}) != len(values):
            errors.append(f"provenance.{name}: entries must be unique")
        for i, value in enumerate(values):
            _match(errors, f"provenance.{name}[{i}]", value, pattern)
    sources = provenance.get("source_artifacts")
    if isinstance(sources, list) and ref.get("artifact_id") in cast(
        list[object], sources
    ):
        errors.append(
            "provenance.source_artifacts: an artifact cannot derive from itself"
        )


@dataclass(frozen=True)
class ArtifactReference:
    """A validated reference; build it with `from_dict()`."""

    data: dict[str, Any]

    @classmethod
    def from_dict(cls, data: object) -> ArtifactReference:
        errors = validate(data)
        if errors:
            raise InvalidReferenceError("; ".join(errors))
        return cls(json.loads(json.dumps(data)))

    def to_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], json.loads(json.dumps(self.data)))

    @property
    def artifact_id(self) -> str:
        return cast(str, self.data["artifact_id"])

    @property
    def lifecycle_status(self) -> str:
        return cast(str, self.data["lifecycle_status"])

    @property
    def consumable(self) -> bool:
        return self.lifecycle_status in CONSUMABLE

    @property
    def digest(self) -> Digest:
        checksum = cast(dict[str, str], self.data["checksum"])
        return Digest(
            checksum["algorithm"], checksum["value"], cast(int, self.data["size_bytes"])
        )

    def verify_bytes(self, data: bytes) -> None:
        """Raise IntegrityError unless `data` is exactly this artifact version."""
        verify(self.digest, digest_bytes(data))

    def require_consumable(self) -> None:
        if not self.consumable:
            raise IntegrityError(
                f"artifact {self.artifact_id} is {self.lifecycle_status}; consumers use only AVAILABLE"
            )

    def with_status(self, status: str) -> ArtifactReference:
        require_transition(self.lifecycle_status, status)
        return replace(self, data={**self.to_dict(), "lifecycle_status": status})
