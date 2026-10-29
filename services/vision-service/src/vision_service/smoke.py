"""CPU-only Vision smoke path (WP-VIS-008; FR-VIS-014, NFR-PERF-009, NFR-RES-007).

`mfgctl smoke vision` runs this module. It needs no GPU, no accelerator runtime and
no platform services: a deterministic SYNTHETIC smoke sample is encoded in memory,
read back through the real `ArtifactStore.read` verification path over an
in-memory S3 client, run through the inspection pipeline and validated against the
registered InspectionObservation v1 contract. Per-image wall time is compared with
the 15 s/image smoke threshold.

The smoke "model" is the F2 baseline detector, distinct from any promoted model.
Each run records the observed host and whether it matches the primary shared-host
HardwareProfile pinned in 01 (Intel Core i7-9700K). The sample is synthetic, not the
accepted small inspection sample NFR-PERF-009 names, so a PASS is a smoke and
characterization result, not NFR-PERF-009 acceptance evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import struct
import sys
import time
import uuid
import zlib
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
from cap_artifacts import ArtifactReference, ArtifactStore, S3Client, digest_bytes
from cap_artifacts import object_key as artifact_key
from numpy.typing import NDArray

from vision_service.pipeline import inspect
from vision_service.request import parse_request

SAMPLE_VERSION = "vision-smoke-synthetic/1"
THRESHOLD_S = 15.0
NAMESPACE = uuid.UUID("5a1e0f3c-6d2b-4c8e-9f10-2b3c4d5e6f70")
WORLD = {"world_id": "world-smoke", "simulation_run_id": None, "branch_id": None}
CONTRACT_ID = "vision.inspection-observation.v1"
PRIMARY_PROFILE_CPU = "i7-9700K"
LIMITATION = (
    "SYNTHETIC smoke sample, not the accepted small inspection sample: "
    "smoke/characterization result, not NFR-PERF-009 acceptance"
)
PACKAGE_SCHEMA = "vision.cpu-smoke-package/v1"
PACKAGE_RELATIVE = Path(
    "services/vision-service/model-packages/vision-baseline-local-deviation/1.0.0/package.json"
)


class SmokeInputError(ValueError):
    """The smoke package or accepted sample manifest is not trustworthy."""


def _cpu_model() -> str | None:
    try:
        text = Path("/proc/cpuinfo").read_text("utf-8")
    except OSError:
        return platform.processor() or None
    for line in text.splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return platform.processor() or None


def _memory_gib() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text("utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) / 1024 / 1024, 1)
    except (OSError, ValueError, IndexError):
        return None
    return None


def host() -> dict[str, Any]:
    cpu = _cpu_model()
    return {
        "cpu_model": cpu,
        "logical_cpus": os.cpu_count(),
        "memory_gib": _memory_gib(),
        "machine": platform.machine(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "hardware_profile": (
            "PRIMARY_SHARED_HOST (01 Final Human Reconciliation)"
            if cpu and PRIMARY_PROFILE_CPU in cpu
            else "UNRECOGNIZED_HOST"
        ),
    }


@dataclass(frozen=True)
class SampleImage:
    name: str
    png: bytes
    expects_candidates: bool


@dataclass(frozen=True)
class SmokePackage:
    package_id: str
    version: str
    algorithm: str
    preprocessing_version: str
    output_schema_version: str
    execution: str
    promoted: bool


def load_package(path: Path) -> SmokePackage:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SmokeInputError("CPU smoke package is unreadable") from None
    required = {
        "schema",
        "package_id",
        "version",
        "algorithm",
        "preprocessing_version",
        "output_schema_version",
        "execution",
        "promoted",
    }
    if not isinstance(value, dict):
        raise SmokeInputError("CPU smoke package manifest fields are invalid")
    manifest = cast(dict[str, object], value)
    if set(manifest) != required:
        raise SmokeInputError("CPU smoke package manifest fields are invalid")
    if manifest["schema"] != PACKAGE_SCHEMA or manifest["execution"] != "CPU_ONLY":
        raise SmokeInputError("CPU smoke package schema or execution is invalid")
    identity_fields = (
        "package_id",
        "version",
        "algorithm",
        "preprocessing_version",
        "output_schema_version",
    )
    if manifest["promoted"] is not False or not all(
        isinstance(manifest[field], str) and cast(str, manifest[field]).strip()
        for field in identity_fields
    ):
        raise SmokeInputError("CPU smoke package identity is invalid")
    return SmokePackage(
        package_id=cast(str, manifest["package_id"]),
        version=cast(str, manifest["version"]),
        algorithm=cast(str, manifest["algorithm"]),
        preprocessing_version=cast(str, manifest["preprocessing_version"]),
        output_schema_version=cast(str, manifest["output_schema_version"]),
        execution=cast(str, manifest["execution"]),
        promoted=cast(bool, manifest["promoted"]),
    )


def load_sample_manifest(path: Path) -> list[SampleImage]:
    """Load an explicitly labelled sample set without guessing labels."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SmokeInputError("sample manifest is unreadable") from None
    if not isinstance(value, dict):
        raise SmokeInputError("sample manifest fields are invalid")
    manifest = cast(dict[str, object], value)
    if set(manifest) != {"schema", "provenance", "images"}:
        raise SmokeInputError("sample manifest fields are invalid")
    if manifest["schema"] != "vision.smoke-sample/v1" or not isinstance(
        manifest["provenance"], str
    ):
        raise SmokeInputError("sample manifest schema or provenance is invalid")
    images = manifest["images"]
    if not isinstance(images, list) or not images:
        raise SmokeInputError("sample manifest needs at least one image")
    images = cast(list[object], images)
    root = path.parent.resolve()
    result: list[SampleImage] = []
    for raw_item in images:
        if not isinstance(raw_item, dict):
            raise SmokeInputError("sample manifest image entry is invalid")
        item = cast(dict[str, object], raw_item)
        if set(item) != {
            "name",
            "path",
            "expects_candidates",
        }:
            raise SmokeInputError("sample manifest image entry is invalid")
        name, relative = item["name"], item["path"]
        if (
            not isinstance(name, str)
            or not name.strip()
            or not isinstance(relative, str)
            or not relative.strip()
            or type(item["expects_candidates"]) is not bool
        ):
            raise SmokeInputError("sample manifest image identity is invalid")
        image_path = (root / relative).resolve()
        if root not in image_path.parents:
            raise SmokeInputError("sample manifest path escapes its directory")
        try:
            data = image_path.read_bytes()
        except OSError:
            raise SmokeInputError("sample manifest image is unreadable") from None
        result.append(SampleImage(name, data, item["expects_candidates"]))
    return result


def encode_gray_png(image: NDArray[np.float64]) -> bytes:
    """8-bit grayscale PNG with filter type 0 on every row."""
    pixels = np.clip(np.round(image * 255.0), 0, 255).astype(np.uint8)
    height, width = pixels.shape
    raw = np.zeros((height, width + 1), dtype=np.uint8)
    raw[:, 1:] = pixels

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind + body) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw.tobytes(), 6))
        + chunk(b"IEND", b"")
    )


def sample(count: int, size: int) -> list[SampleImage]:
    """Deterministic synthetic sample: even indexes carry one planted bright defect."""
    images: list[SampleImage] = []
    for index in range(count):
        rng = np.random.default_rng(1000 + index)
        image = np.clip(rng.normal(0.4, 0.03, (size, size)), 0.0, 1.0)
        planted = index % 2 == 0
        if planted:
            top = int(rng.integers(0, size - 8))
            left = int(rng.integers(0, size - 24))
            image[top : top + 4, left : left + 20] = 1.0
        images.append(
            SampleImage(f"smoke-{index:02d}", encode_gray_png(image), planted)
        )
    return images


class _MemoryS3:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def get_object(self, bucket: str, key: str) -> bytes:
        return self.objects[(bucket, key)]


def _reference(image: SampleImage, client: _MemoryS3) -> ArtifactReference:
    artifact_id = str(uuid.uuid5(NAMESPACE, image.name))
    object_id = str(uuid.uuid5(NAMESPACE, image.name + "/object"))
    key = artifact_key("inspection_image", artifact_id, 1, object_id)
    digest = digest_bytes(image.png)
    ref = ArtifactReference.from_dict(
        {
            "schema": "cap.artifact-ref/v1",
            "artifact_id": artifact_id,
            "version": 1,
            "artifact_type": "inspection_image",
            "artifact_class": "OPERATIONAL_EVIDENCE",
            "format_version": "png/1",
            "content_type": "image/png",
            "size_bytes": digest.size_bytes,
            "checksum": {"algorithm": digest.algorithm, "value": digest.value},
            "logical_owner": "vision-service",
            "producer": {"service": "vision-smoke", "version": SAMPLE_VERSION},
            "created_at": "2026-10-28T00:00:00Z",
            "context": dict(WORLD),
            "classification": "INTERNAL",
            "retention_class": "RC-D",
            "storage": {
                "bucket": "cap-artifacts-rc-d",
                "key": key,
                "object_id": object_id,
            },
            "lifecycle_status": "AVAILABLE",
            "provenance": {"source_artifacts": [], "source_refs": []},
        }
    )
    client.objects[("cap-artifacts-rc-d", key)] = image.png
    return ref


def _request(image: SampleImage, ref: ArtifactReference) -> dict[str, Any]:
    return {
        "inspection_request_id": f"IR-{image.name}",
        "inspection_run_id": f"IRUN-{image.name}",
        "world_id": WORLD["world_id"],
        "subject": {
            "lot_id": "L-SMOKE",
            "lot_revision": "lot-smoke-1",
            "serialized_component_id": f"C-{image.name}",
            "serialized_component_revision": "component-smoke-1",
            "route_visit_id": "V-SMOKE-INSPECT",
        },
        "artifact": ref.to_dict(),
    }


def _validator(root: Path) -> Any:
    from cap_contracts import BoundaryValidator, Registry

    registry = Registry.load(root / "packages/contracts/registry")
    return BoundaryValidator(registry.get(CONTRACT_ID), root)


def run(
    count: int = 8,
    size: int = 512,
    root: Path | None = None,
    *,
    package_path: Path | None = None,
    sample_manifest: Path | None = None,
) -> dict[str, Any]:
    root = root or Path.cwd()
    package = load_package(package_path or root / PACKAGE_RELATIVE)
    validator = _validator(root)
    client = _MemoryS3()
    store = ArtifactStore(cast(S3Client, client))
    if sample_manifest is None:
        if count < 1:
            raise ValueError("the smoke sample needs at least one image")
        images = sample(count, size)
        provenance = "SYNTHETIC"
    else:
        images = load_sample_manifest(sample_manifest)
        provenance = "EXTERNAL_MANIFEST"
    results: list[dict[str, Any]] = []
    pipeline: dict[str, Any] = {}
    for image in images:
        work = parse_request(_request(image, _reference(image, client)))
        started = time.perf_counter()
        observation = inspect(
            work,
            store,
            observation_id=str(uuid.uuid4()),
            clock=lambda: datetime.now(UTC),
        )
        elapsed = time.perf_counter() - started
        validator.validate(observation, role="producer")
        pipeline = observation["pipeline_identity"]
        found = observation["outcome"] == "DEFECT_CANDIDATES"
        results.append(
            {
                "image": image.name,
                "seconds": round(elapsed, 4),
                "outcome": observation["outcome"],
                "expected_candidates": image.expects_candidates,
                "functional_ok": found == image.expects_candidates,
            }
        )
    seconds = [item["seconds"] for item in results]
    within = max(seconds) <= THRESHOLD_S
    functional = all(item["functional_ok"] for item in results)
    if (
        not pipeline["models"]
        or pipeline["models"][0]["model_package_id"] != package.package_id
    ):
        raise SmokeInputError("smoke package does not match pipeline model identity")
    if pipeline["models"][0]["model_version"] != package.version:
        raise SmokeInputError("smoke package version does not match pipeline identity")
    sample_report: dict[str, Any] = {
        "version": SAMPLE_VERSION,
        "images": len(images),
        "size_px": [size, size],
        "provenance": provenance,
    }
    if sample_manifest is not None:
        sample_report["manifest"] = str(sample_manifest)
    return {
        "schema": "vision.smoke/v1",
        "result": "PASS" if within and functional else "FAIL",
        "sample": sample_report,
        "package": {
            "schema": PACKAGE_SCHEMA,
            "package_id": package.package_id,
            "version": package.version,
            "algorithm": package.algorithm,
            "execution": package.execution,
            "promoted": package.promoted,
        },
        "pipeline": pipeline,
        "threshold_s_per_image": THRESHOLD_S,
        "max_s_per_image": max(seconds),
        "mean_s_per_image": round(sum(seconds) / len(seconds), 4),
        "functional_ok": functional,
        "accelerator_used": False,
        "host": host(),
        "limitation": LIMITATION,
        "images": results,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mfgctl smoke vision", description=__doc__)
    parser.add_argument("--images", type=int, default=8)
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--sample-manifest", type=Path)
    parser.add_argument("--json", action="store_true", help="print the full report")
    args = parser.parse_args(argv)
    if args.images < 1 or not 16 <= args.size <= 4096:
        parser.error("--images must be >= 1 and --size between 16 and 4096")
    report = run(args.images, args.size, sample_manifest=args.sample_manifest)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(
            f"vision smoke {report['result']}: {report['sample']['images']} synthetic "
            f"{args.size}x{args.size} images, max {report['max_s_per_image']} s/image "
            f"(threshold {THRESHOLD_S} s), mean {report['mean_s_per_image']} s/image, "
            f"functional {'ok' if report['functional_ok'] else 'FAILED'}, CPU only"
        )
        print(
            f"host: {report['host']['cpu_model']} ({report['host']['hardware_profile']})"
        )
        print(report["limitation"])
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
