"""Bucket, key and lifecycle conventions for artifact storage (WP-OBJ-001).

02 Large Artifact Policy: a bucket or object key is never a business identity or a
cross-service contract; every upload gets its own physical-object identity; a
finalized object is never overwritten; normal consumers use only AVAILABLE
artifacts. Buckets follow the 02 recovery classes because backup duty differs:
RC-B critical artifacts need a verified off-host copy, RC-C is rebuildable, RC-D
is disposable.
"""

from __future__ import annotations

import re
import uuid

KEY_LAYOUT = "v1"

BUCKETS: dict[str, str] = {
    "RC-B": "cap-artifacts-rc-b",
    "RC-C": "cap-artifacts-rc-c",
    "RC-D": "cap-artifacts-rc-d",
}

ARTIFACT_CLASSES = frozenset(
    {
        "SOURCE_CANONICAL",
        "VERSIONED_RELEASE",
        "DERIVED_REBUILDABLE",
        "OPERATIONAL_EVIDENCE",
        "SNAPSHOT_CHECKPOINT",
        "EXPERIMENT_ARTIFACT",
        "TEMPORARY_STAGING",
    }
)
CLASSIFICATIONS = frozenset(
    {"PUBLIC_INTERNAL", "INTERNAL", "SENSITIVE", "RESTRICTED_ORACLE"}
)

# 02 lifecycle: RESERVED -> UPLOADING -> VALIDATING -> AVAILABLE with failure states,
# then AVAILABLE -> RETIRED/DELETE_ELIGIBLE -> PENDING_DELETE -> DELETED.
TRANSITIONS: dict[str, frozenset[str]] = {
    "RESERVED": frozenset({"UPLOADING", "ABORTED"}),
    "UPLOADING": frozenset({"VALIDATING", "FAILED", "ABORTED"}),
    "VALIDATING": frozenset({"AVAILABLE", "FAILED", "QUARANTINED"}),
    "AVAILABLE": frozenset({"QUARANTINED", "RETIRED", "DELETE_ELIGIBLE"}),
    "QUARANTINED": frozenset({"DELETE_ELIGIBLE"}),
    "FAILED": frozenset({"DELETE_ELIGIBLE"}),
    "ABORTED": frozenset({"DELETE_ELIGIBLE"}),
    "RETIRED": frozenset({"DELETE_ELIGIBLE"}),
    "DELETE_ELIGIBLE": frozenset({"PENDING_DELETE"}),
    "PENDING_DELETE": frozenset({"DELETED"}),
    "DELETED": frozenset(),
}
LIFECYCLE = frozenset(TRANSITIONS)
CONSUMABLE = frozenset({"AVAILABLE"})

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TYPE_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


class ConventionError(ValueError):
    """A value breaks the storage convention."""


def new_id() -> str:
    """A fresh random identity (artifact_id or object_id)."""
    return str(uuid.uuid4())


def bucket_for(retention_class: str) -> str:
    try:
        return BUCKETS[retention_class]
    except KeyError:
        raise ConventionError(
            f"retention class {retention_class!r} has no artifact bucket (RC-A is not an artifact)"
        ) from None


def object_key(artifact_type: str, artifact_id: str, object_id: str) -> str:
    """v1/<artifact_type>/<shard>/<artifact_id>/<object_id>; identities only."""
    if not TYPE_RE.match(artifact_type):
        raise ConventionError(f"invalid artifact_type {artifact_type!r}")
    for name, value in (("artifact_id", artifact_id), ("object_id", object_id)):
        if not UUID_RE.match(value):
            raise ConventionError(f"{name} must be a lowercase UUID, got {value!r}")
    return f"{KEY_LAYOUT}/{artifact_type}/{artifact_id[:2]}/{artifact_id}/{object_id}"


def can_transition(source: str, target: str) -> bool:
    return target in TRANSITIONS.get(source, frozenset())


def require_transition(source: str, target: str) -> None:
    if source not in LIFECYCLE or target not in LIFECYCLE:
        raise ConventionError(f"unknown lifecycle status in {source!r} -> {target!r}")
    if not can_transition(source, target):
        raise ConventionError(
            f"lifecycle transition {source} -> {target} is not allowed"
        )
