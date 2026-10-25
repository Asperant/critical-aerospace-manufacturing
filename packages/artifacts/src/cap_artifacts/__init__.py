"""cap-artifacts — ArtifactReference contract and storage conventions (WP-OBJ-001)."""

from cap_artifacts.conventions import (
    BUCKETS,
    ConventionError,
    bucket_for,
    can_transition,
    new_id,
    object_key,
    require_transition,
    version_prefix,
)
from cap_artifacts.errors import MissingObjectError, OverwriteError, StoreError
from cap_artifacts.integrity import (
    Digest,
    IntegrityError,
    digest_bytes,
    digest_chunks,
    digest_stream,
    verify,
)
from cap_artifacts.reference import (
    SCHEMA_ID,
    ArtifactReference,
    InvalidReferenceError,
    schema,
    validate,
)
from cap_artifacts.sigv4 import Credentials
from cap_artifacts.store import ArtifactStore, S3Client, StoreConfig, VersionRegistry

__all__ = [
    "ArtifactStore",
    "Credentials",
    "MissingObjectError",
    "OverwriteError",
    "S3Client",
    "StoreConfig",
    "StoreError",
    "VersionRegistry",
    "version_prefix",
    "BUCKETS",
    "SCHEMA_ID",
    "ArtifactReference",
    "ConventionError",
    "Digest",
    "IntegrityError",
    "InvalidReferenceError",
    "bucket_for",
    "can_transition",
    "digest_bytes",
    "digest_chunks",
    "digest_stream",
    "new_id",
    "object_key",
    "require_transition",
    "schema",
    "validate",
    "verify",
]
