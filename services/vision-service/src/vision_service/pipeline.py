"""Inspection pipeline: request -> artifact read -> preprocessing -> inference ->
InspectionObservation v1 payload (02: InspectionRequested -> Artifact Retrieval ->
Inference -> Structured InspectionObservation).

Artifact integrity failures (unavailable, missing or checksum mismatch) raise and
produce no observation: they are infrastructure faults, never perception results.
An artifact that is readable but not an evaluable image yields NOT_EVALUATED.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from cap_artifacts import ArtifactReference

from vision_service.baseline import (
    MODEL_PACKAGE_ID,
    MODEL_VERSION,
    Candidate,
    ThresholdPolicy,
    detect,
)
from vision_service.png import ImageDecodeError, decode_png
from vision_service.preprocessing import PREPROCESSING_VERSION, preprocess
from vision_service.request import InspectionWork

OUTPUT_SCHEMA_VERSION = "vision.inspection-observation.v1"
EVENT_TYPE = "vision.inspection-observation"
SUPPORTED_CONTENT_TYPE = "image/png"


class ArtifactReader(Protocol):
    """cap_artifacts.ArtifactStore satisfies this: verified reads of AVAILABLE versions."""

    def read(self, ref: ArtifactReference) -> bytes: ...


def _instant(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("clock must return an aware UTC datetime")
    utc = value.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _identity(ref: ArtifactReference) -> dict[str, Any]:
    data = ref.data
    return {
        "ref_schema": data["schema"],
        "artifact_id": data["artifact_id"],
        "version": data["version"],
        "artifact_type": data["artifact_type"],
        "checksum": dict(cast(dict[str, str], data["checksum"])),
    }


def _defect(index: int, candidate: Candidate) -> dict[str, Any]:
    return {
        "defect_id": f"D-{index}",
        "open_set_decision": "UNKNOWN_REVIEW_REQUIRED",
        "class_label": None,
        "class_confidence": None,
        "anomaly_score": round(candidate.score, 6),
        "localization": {
            "kind": "BBOX",
            "frame": "IMAGE_NORMALIZED",
            "x": round(candidate.x, 6),
            "y": round(candidate.y, 6),
            "width": round(candidate.width, 6),
            "height": round(candidate.height, 6),
        },
        "mask_artifact": None,
        "area_fraction": round(candidate.area_fraction, 6),
    }


def inspect(
    work: InspectionWork,
    reader: ArtifactReader,
    *,
    observation_id: str,
    clock: Callable[[], datetime],
    policy: ThresholdPolicy | None = None,
) -> dict[str, Any]:
    """Return one InspectionObservation v1 payload for `work`."""
    policy = policy or ThresholdPolicy()
    started = clock()
    data = reader.read(work.artifact)

    quality, flags = "VALID", ()
    defects: list[dict[str, Any]] = []
    image_score: float | None = None
    truncated = False
    if work.artifact.data["content_type"] != SUPPORTED_CONTENT_TYPE:
        quality, flags = "INVALID_INPUT", ("UNSUPPORTED_FORMAT",)
    else:
        try:
            pixels = decode_png(data)
        except ImageDecodeError:
            quality, flags = "INVALID_INPUT", ("UNDECODABLE_IMAGE",)
        else:
            prepared = preprocess(pixels)
            quality, flags = prepared.quality, prepared.flags
            if quality != "INVALID_INPUT":
                detection = detect(prepared.image, policy)
                defects = [
                    _defect(index, candidate)
                    for index, candidate in enumerate(detection.candidates, start=1)
                ]
                image_score = round(detection.image_score, 6)
                truncated = detection.truncated

    if quality == "INVALID_INPUT":
        outcome = "NOT_EVALUATED"
    else:
        outcome = "DEFECT_CANDIDATES" if defects else "NO_DEFECT_CANDIDATES"
    completed = clock()
    context = cast(dict[str, Any], work.artifact.data["context"])
    return {
        "event_type": EVENT_TYPE,
        "schema_version": 1,
        "observation_id": observation_id,
        "inspection_request_id": work.inspection_request_id,
        "inspection_run_id": work.inspection_run_id,
        "subject": work.subject.to_dict(),
        "context": {
            "world_id": work.world_id,
            "simulation_run_id": context["simulation_run_id"],
            "branch_id": context["branch_id"],
        },
        "source_artifact": _identity(work.artifact),
        "outcome": outcome,
        "review_required": bool(defects) or truncated or quality != "VALID",
        "data_quality": {"status": quality, "flags": list(flags)},
        "defects": defects,
        "image_anomaly_score": image_score,
        "confidence_calibration": "UNCALIBRATED",
        "pipeline_identity": {
            "models": [
                {
                    "task": "BASELINE_ALGORITHM",
                    "model_package_id": MODEL_PACKAGE_ID,
                    "model_version": MODEL_VERSION,
                }
            ],
            "preprocessing_version": PREPROCESSING_VERSION,
            "threshold_policy_version": policy.version,
            "output_schema_version": OUTPUT_SCHEMA_VERSION,
        },
        "inference": {
            "started_at": _instant(started),
            "completed_at": _instant(completed),
            "latency_ms": round(
                max((completed - started).total_seconds(), 0.0) * 1000, 3
            ),
        },
    }
