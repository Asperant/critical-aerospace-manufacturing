"""ArtifactReference contract and conventions (WP-OBJ-001, TEST-OBJ-001-001).

Every negative case is checked twice: by the package validator and by the
published JSON Schema where the rule is structural, so the two cannot drift.
"""

from __future__ import annotations

import copy
import io
import json
from importlib import resources
from typing import Any

import pytest
from cap_artifacts import (
    BUCKETS,
    ArtifactReference,
    ConventionError,
    IntegrityError,
    InvalidReferenceError,
    bucket_for,
    can_transition,
    digest_bytes,
    digest_chunks,
    digest_stream,
    new_id,
    object_key,
    require_transition,
    schema,
    validate,
    verify,
)
from jsonschema import Draft202012Validator

EXAMPLE_BYTES = b"hello world"


def example() -> dict[str, Any]:
    text = resources.files("cap_artifacts").joinpath("schemas/artifact-reference.json")
    return json.loads(text.read_text("utf-8"))


def schema_errors(data: object) -> list[str]:
    return [e.message for e in Draft202012Validator(schema()).iter_errors(data)]


def test_example_is_valid_for_schema_and_package() -> None:
    Draft202012Validator.check_schema(schema())
    assert schema_errors(example()) == []
    assert validate(example()) == []


def test_example_bytes_match_the_example_checksum() -> None:
    ref = ArtifactReference.from_dict(example())
    ref.verify_bytes(EXAMPLE_BYTES)
    assert ref.consumable


def set_path(data: dict[str, Any], path: str, value: object) -> dict[str, Any]:
    result = copy.deepcopy(data)
    *parents, last = path.split(".")
    target = result
    for part in parents:
        target = target[part]
    if value is DELETE:
        del target[last]
    else:
        target[last] = value
    return result


DELETE = object()

# (path, value, expected package message, also rejected by the schema)
STRUCTURAL = [
    ("schema", "cap.artifact-ref/v2", "schema: must be", True),
    ("artifact_id", "IR-2026-0001", "artifact_id", True),
    ("artifact_id", "3F2B6C1E-8D4A-4E7B-9A21-5C0D7E9F1A42", "artifact_id", True),
    ("version", 0, "version", True),
    ("version", True, "version", True),
    ("artifact_type", "Inspection Image", "artifact_type", True),
    ("artifact_class", "FINAL", "artifact_class", True),
    ("content_type", "PNG", "content_type", True),
    ("size_bytes", -1, "size_bytes", True),
    ("checksum.algorithm", "md5", "checksum.algorithm", True),
    ("checksum.value", "B94D27B9", "checksum.value", True),
    ("logical_owner", "Vision Service", "logical_owner", True),
    ("producer.version", "", "producer.version", True),
    ("created_at", "2026-10-25 09:00:00", "created_at", True),
    ("context.world_id", "", "context.world_id", True),
    ("classification", "SECRET", "classification", True),
    ("retention_class", "RC-A", "retention_class", True),
    ("storage.bucket", "public", "storage.bucket", True),
    ("lifecycle_status", "READY", "lifecycle_status", True),
    ("provenance.source_refs", ["no-kind"], "provenance.source_refs", True),
    ("provenance.source_artifacts", ["x", "x"], "provenance.source_artifacts", True),
    ("storage", DELETE, "missing storage", True),
    ("payload", "aGVsbG8=", "unexpected payload", True),
]

# Rules the schema cannot express; only the package validator enforces them.
SEMANTIC = [
    ("storage.bucket", "cap-artifacts-rc-c", "RC-B artifacts live in cap-artifacts-rc-b"),
    ("storage.key", "v1/inspection_image/3f/3f2b6c1e-8d4a-4e7b-9a21-5c0d7e9f1a42/"
     "00000000-0000-4000-8000-000000000000", "derived from identities only"),
    ("provenance.source_artifacts", ["3f2b6c1e-8d4a-4e7b-9a21-5c0d7e9f1a42"], "derive from itself"),
    ("artifact_class", "TEMPORARY_STAGING", "TEMPORARY_STAGING artifacts must be RC-D"),
]  # fmt: skip


@pytest.mark.parametrize(("path", "value", "message", "schema_rejects"), STRUCTURAL)
def test_structural_violations_are_rejected_by_both(
    path: str, value: object, message: str, schema_rejects: bool
) -> None:
    data = set_path(example(), path, value)
    found = validate(data)
    assert any(message in e for e in found), found
    assert bool(schema_errors(data)) is schema_rejects
    with pytest.raises(InvalidReferenceError):
        ArtifactReference.from_dict(data)


@pytest.mark.parametrize(("path", "value", "message"), SEMANTIC)
def test_semantic_violations_are_rejected(
    path: str, value: object, message: str
) -> None:
    data = set_path(example(), path, value)
    assert any(message in e for e in validate(data)), validate(data)


def test_non_object_is_rejected() -> None:
    assert validate([]) == ["reference must be an object"]


def test_object_key_uses_identities_only_and_is_unique_per_upload() -> None:
    artifact_id = new_id()
    first, second = (
        object_key("inspection_image", artifact_id, new_id()) for _ in range(2)
    )
    assert first != second
    assert first.startswith(f"v1/inspection_image/{artifact_id[:2]}/{artifact_id}/")
    with pytest.raises(ConventionError):
        object_key("inspection_image", "LOT-42", new_id())
    with pytest.raises(ConventionError):
        object_key("../etc", artifact_id, new_id())


def test_bucket_follows_retention_class() -> None:
    assert bucket_for("RC-B") == "cap-artifacts-rc-b"
    assert set(BUCKETS) == {"RC-B", "RC-C", "RC-D"}
    with pytest.raises(ConventionError, match="RC-A is not an artifact"):
        bucket_for("RC-A")


@pytest.mark.parametrize(
    ("source", "target", "allowed"),
    [
        ("RESERVED", "UPLOADING", True),
        ("UPLOADING", "VALIDATING", True),
        ("VALIDATING", "AVAILABLE", True),
        ("VALIDATING", "QUARANTINED", True),
        ("AVAILABLE", "UPLOADING", False),
        ("AVAILABLE", "VALIDATING", False),
        ("RESERVED", "AVAILABLE", False),
        ("DELETED", "AVAILABLE", False),
        ("PENDING_DELETE", "DELETED", True),
    ],
)
def test_lifecycle_transitions(source: str, target: str, allowed: bool) -> None:
    assert can_transition(source, target) is allowed
    if not allowed:
        with pytest.raises(ConventionError):
            require_transition(source, target)


def test_finalized_artifact_cannot_go_back_to_upload() -> None:
    ref = ArtifactReference.from_dict(example())
    with pytest.raises(ConventionError):
        ref.with_status("UPLOADING")
    retired = ref.with_status("RETIRED")
    assert retired.lifecycle_status == "RETIRED"
    assert ref.lifecycle_status == "AVAILABLE"  # the original stays immutable


def test_only_available_artifacts_are_consumable() -> None:
    data = set_path(example(), "lifecycle_status", "VALIDATING")
    ref = ArtifactReference.from_dict(data)
    assert not ref.consumable
    with pytest.raises(IntegrityError, match="consumers use only AVAILABLE"):
        ref.require_consumable()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (b"hello worle", "checksum mismatch"),
        (b"hello world!", "size mismatch"),
        (b"", "size mismatch"),
    ],
)
def test_corrupted_bytes_fail_closed(payload: bytes, message: str) -> None:
    ref = ArtifactReference.from_dict(example())
    with pytest.raises(IntegrityError, match=message):
        ref.verify_bytes(payload)


def test_streamed_and_chunked_digests_agree() -> None:
    data = bytes(range(256)) * 5000
    whole = digest_bytes(data)
    assert digest_stream(io.BytesIO(data), chunk=4096) == whole
    assert digest_chunks([data[:7], data[7:]]) == whole
    with pytest.raises(IntegrityError, match="algorithm"):
        verify(whole, type(whole)("blake2b", whole.value, whole.size_bytes))


def test_reference_round_trips_without_sharing_state() -> None:
    data = example()
    ref = ArtifactReference.from_dict(data)
    data["size_bytes"] = 999
    assert ref.to_dict()["size_bytes"] == len(EXAMPLE_BYTES)
    assert ArtifactReference.from_dict(ref.to_dict()) == ref
