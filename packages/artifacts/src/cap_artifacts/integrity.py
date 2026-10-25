"""Content identity: compute and verify checksums (NFR-DATA-001, WP-OBJ-001).

SHA-256 is the algorithm of `cap.artifact-ref/v1`; the reference names it
explicitly so a later change is an additive schema version. Verification fails
closed: a size or digest mismatch raises and nothing is returned to the caller.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from typing import BinaryIO

ALGORITHM = "sha256"
CHUNK = 1024 * 1024


class IntegrityError(ValueError):
    """Bytes do not match the content identity recorded for them."""


@dataclass(frozen=True)
class Digest:
    algorithm: str
    value: str
    size_bytes: int


def digest_bytes(data: bytes) -> Digest:
    return Digest(ALGORITHM, hashlib.sha256(data).hexdigest(), len(data))


def digest_chunks(chunks: Iterable[bytes]) -> Digest:
    hasher = hashlib.sha256()
    size = 0
    for chunk in chunks:
        hasher.update(chunk)
        size += len(chunk)
    return Digest(ALGORITHM, hasher.hexdigest(), size)


def digest_stream(stream: BinaryIO, chunk: int = CHUNK) -> Digest:
    return digest_chunks(iter(lambda: stream.read(chunk), b""))


def verify(expected: Digest, actual: Digest) -> None:
    if expected.algorithm != actual.algorithm:
        raise IntegrityError(
            f"checksum algorithm {actual.algorithm} cannot verify {expected.algorithm}"
        )
    if expected.size_bytes != actual.size_bytes:
        raise IntegrityError(
            f"size mismatch: expected {expected.size_bytes} bytes, got {actual.size_bytes}"
        )
    if expected.value != actual.value:
        raise IntegrityError(
            f"checksum mismatch: expected {expected.value[:12]}…, got {actual.value[:12]}…"
        )
