"""Shared helpers: a reference PNG encoder, artifact references with real
checksums and an ArtifactStore over an in-memory S3 client, so reads go through
the real AVAILABLE and checksum verification path of cap_artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import zlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from cap_artifacts import ArtifactReference, ArtifactStore, S3Client
from cap_contracts import BoundaryValidator, Registry
from numpy.typing import NDArray

REPO = Path(__file__).resolve().parents[3]
ARTIFACT_EXAMPLE = (
    REPO / "packages/artifacts/src/cap_artifacts/schemas/artifact-reference.json"
)
COLOR_TYPES = {1: 0, 2: 4, 3: 2, 4: 6}


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def _filter_row(kind: int, row: bytes, prior: bytes, bpp: int) -> bytes:
    out = bytearray()
    for x, value in enumerate(row):
        left = row[x - bpp] if x >= bpp else 0
        up = prior[x]
        up_left = prior[x - bpp] if x >= bpp else 0
        predictor = {
            0: 0,
            1: left,
            2: up,
            3: (left + up) // 2,
            4: _paeth(left, up, up_left),
        }[kind]
        out.append((value - predictor) & 0xFF)
    return bytes(out)


def chunk(kind: bytes, body: bytes) -> bytes:
    crc = zlib.crc32(kind + body) & 0xFFFFFFFF
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)


def encode_png(pixels: NDArray[np.uint8], filter_kind: int = 0) -> bytes:
    """Encode (height, width, channels) uint8 pixels with one filter type per row."""
    height, width, channels = pixels.shape
    bpp = channels
    raw = bytearray()
    prior = bytes(width * bpp)
    for y in range(height):
        row = pixels[y].tobytes()
        raw.append(filter_kind)
        raw.extend(_filter_row(filter_kind, row, prior, bpp))
        prior = row
    header = struct.pack(">IIBBBBB", width, height, 8, COLOR_TYPES[channels], 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw)))
        + chunk(b"IEND", b"")
    )


def gray(values: NDArray[np.float64]) -> NDArray[np.uint8]:
    clipped = np.clip(np.round(values * 255.0), 0, 255).astype(np.uint8)
    return clipped[:, :, np.newaxis]


def textured(seed: int = 7, size: int = 64) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(0.4, 0.03, (size, size)), 0.0, 1.0)


def reference_for(data: bytes, **overrides: Any) -> dict[str, Any]:
    ref = cast(dict[str, Any], json.loads(ARTIFACT_EXAMPLE.read_text("utf-8")))
    ref["size_bytes"] = len(data)
    ref["checksum"] = {"algorithm": "sha256", "value": hashlib.sha256(data).hexdigest()}
    for key, value in overrides.items():
        ref[key] = value
    return ref


def request_for(ref: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    request: dict[str, Any] = {
        "inspection_request_id": "IR-2026-0001",
        "inspection_run_id": "IRUN-2026-0001-a",
        "world_id": ref["context"]["world_id"],
        "subject": {
            "lot_id": "L-REENTRANT-2",
            "lot_revision": "lot-r6",
            "serialized_component_id": "C-REENTRANT-1",
            "serialized_component_revision": "component-r7",
            "route_visit_id": "V-10",
        },
        "artifact": copy.deepcopy(ref),
    }
    request.update(overrides)
    return request


class MemoryS3:
    """The single S3Client method ArtifactStore.read needs."""

    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put(self, ref: dict[str, Any], data: bytes) -> None:
        storage = ref["storage"]
        self.objects[(storage["bucket"], storage["key"])] = data

    def get_object(self, bucket: str, key: str) -> bytes:
        return self.objects[(bucket, key)]


def store_with(ref: dict[str, Any], data: bytes) -> ArtifactStore:
    client = MemoryS3()
    client.put(ref, data)
    return ArtifactStore(cast(S3Client, client))


def as_ref(ref: dict[str, Any]) -> ArtifactReference:
    return ArtifactReference.from_dict(ref)


@pytest.fixture
def clock() -> Iterator[Any]:
    ticks = iter(
        datetime(2026, 10, 25, 9, 0, 1, tzinfo=UTC) + timedelta(milliseconds=250 * n)
        for n in range(1000)
    )
    yield lambda: next(ticks)


@pytest.fixture(scope="session")
def observation_validator() -> BoundaryValidator:
    registry = Registry.load(REPO / "packages/contracts/registry")
    return BoundaryValidator(registry.get("vision.inspection-observation.v1"), REPO)
