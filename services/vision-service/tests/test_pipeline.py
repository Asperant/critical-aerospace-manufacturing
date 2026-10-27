"""TEST-VIS-PIPELINE: artifact reference -> verified read -> preprocessing ->
baseline inference -> InspectionObservation v1, validated against the
registered contract. Artifacts are SYNTHETIC TEST images built in the test."""

from typing import Any

import numpy as np
import pytest
from cap_artifacts import IntegrityError
from cap_contracts import BoundaryValidator
from conftest import encode_png, gray, reference_for, request_for, store_with, textured
from numpy.typing import NDArray
from vision_service import ThresholdPolicy, inspect, parse_request

OBSERVATION_ID = "6d1f0a52-3c7e-4b9a-8f21-0e4d5c6b7a81"


def with_defect() -> NDArray[np.float64]:
    image = textured()
    image[30:33, 20:26] = 1.0
    return image


def run(
    data: bytes,
    clock: Any,
    validator: BoundaryValidator,
    ref_overrides: dict[str, Any] | None = None,
    policy: ThresholdPolicy | None = None,
) -> dict[str, Any]:
    ref = reference_for(data, **(ref_overrides or {}))
    work = parse_request(request_for(ref))
    observation = inspect(
        work,
        store_with(ref, data),
        observation_id=OBSERVATION_ID,
        clock=clock,
        policy=policy,
    )
    validator.validate(observation, role="producer")
    validator.validate(observation, role="consumer")
    return observation


def test_planted_defect_is_found_and_localized(
    clock: Any, observation_validator: BoundaryValidator
) -> None:
    observation = run(encode_png(gray(with_defect())), clock, observation_validator)
    assert observation["outcome"] == "DEFECT_CANDIDATES"
    assert observation["data_quality"] == {"status": "VALID", "flags": []}
    assert observation["review_required"] is True
    assert len(observation["defects"]) == 1
    defect = observation["defects"][0]
    assert defect["open_set_decision"] == "UNKNOWN_REVIEW_REQUIRED"
    assert defect["class_label"] is None and defect["class_confidence"] is None
    box = defect["localization"]
    assert (box["x"], box["y"]) == (20 / 64, 30 / 64)
    assert (box["width"], box["height"]) == (6 / 64, 3 / 64)
    assert defect["area_fraction"] == round(18 / 4096, 6)
    assert observation["image_anomaly_score"] == defect["anomaly_score"] > 6.0


def test_observation_carries_identity_provenance_and_timing(
    clock: Any, observation_validator: BoundaryValidator
) -> None:
    data = encode_png(gray(with_defect()))
    observation = run(data, clock, observation_validator)
    ref = reference_for(data)
    assert observation["subject"]["serialized_component_id"] == "C-REENTRANT-1"
    assert observation["source_artifact"]["checksum"] == ref["checksum"]
    assert observation["context"] == ref["context"]
    assert observation["pipeline_identity"] == {
        "models": [
            {
                "task": "BASELINE_ALGORITHM",
                "model_package_id": "vision-baseline-local-deviation",
                "model_version": "1.0.0",
            }
        ],
        "preprocessing_version": "vision-prep-gray-unit/1",
        "threshold_policy_version": "vision-tp-baseline-z6/1",
        "output_schema_version": "vision.inspection-observation.v1",
    }
    assert observation["confidence_calibration"] == "UNCALIBRATED"
    assert observation["inference"] == {
        "started_at": "2026-10-25T09:00:01.000Z",
        "completed_at": "2026-10-25T09:00:01.250Z",
        "latency_ms": 250.0,
    }


def test_clean_texture_has_no_defect_candidates(
    clock: Any, observation_validator: BoundaryValidator
) -> None:
    observation = run(encode_png(gray(textured())), clock, observation_validator)
    assert observation["outcome"] == "NO_DEFECT_CANDIDATES"
    assert observation["defects"] == []
    assert observation["review_required"] is False
    assert observation["image_anomaly_score"] is not None


def test_low_contrast_input_is_degraded_and_sent_to_review(
    clock: Any, observation_validator: BoundaryValidator
) -> None:
    flat = np.full((32, 32), 0.5)
    observation = run(encode_png(gray(flat)), clock, observation_validator)
    assert observation["data_quality"] == {
        "status": "DEGRADED_INPUT",
        "flags": ["LOW_CONTRAST"],
    }
    assert observation["outcome"] == "NO_DEFECT_CANDIDATES"
    assert observation["review_required"] is True


@pytest.mark.parametrize(
    ("data", "overrides", "flag"),
    [
        (b"not an image at all", None, "UNDECODABLE_IMAGE"),
        (encode_png(gray(np.full((8, 8), 0.5))), None, "IMAGE_TOO_SMALL"),
        (
            encode_png(gray(textured())),
            {"content_type": "image/tiff"},
            "UNSUPPORTED_FORMAT",
        ),
    ],
)
def test_unevaluable_input_is_not_evaluated_never_no_defect(
    data: bytes,
    overrides: dict[str, Any] | None,
    flag: str,
    clock: Any,
    observation_validator: BoundaryValidator,
) -> None:
    observation = run(data, clock, observation_validator, overrides)
    assert observation["outcome"] == "NOT_EVALUATED"
    assert observation["data_quality"] == {"status": "INVALID_INPUT", "flags": [flag]}
    assert observation["defects"] == []
    assert observation["image_anomaly_score"] is None
    assert observation["review_required"] is True


def test_checksum_mismatch_raises_and_produces_no_observation(clock: Any) -> None:
    data = encode_png(gray(with_defect()))
    ref = reference_for(data)
    work = parse_request(request_for(ref))
    tampered = encode_png(gray(textured()))
    with pytest.raises(IntegrityError):
        inspect(
            work, store_with(ref, tampered), observation_id=OBSERVATION_ID, clock=clock
        )


def test_unavailable_artifact_is_not_read(clock: Any) -> None:
    data = encode_png(gray(with_defect()))
    ref = reference_for(data, lifecycle_status="QUARANTINED")
    work = parse_request(request_for(ref))
    with pytest.raises(IntegrityError, match="AVAILABLE"):
        inspect(work, store_with(ref, data), observation_id=OBSERVATION_ID, clock=clock)


def test_inference_is_deterministic_for_the_same_input(
    clock: Any, observation_validator: BoundaryValidator
) -> None:
    data = encode_png(gray(with_defect()), filter_kind=4)
    first = run(data, clock, observation_validator)
    second = run(data, clock, observation_validator)
    for observation in (first, second):
        del observation["inference"]
    assert first == second


def test_candidate_limit_forces_review(
    clock: Any, observation_validator: BoundaryValidator
) -> None:
    image = textured()
    for row in range(4, 60, 8):
        for col in range(4, 60, 8):
            image[row : row + 2, col : col + 2] = 1.0
    policy = ThresholdPolicy(version="vision-tp-test-cap/1", max_candidates=5)
    observation = run(
        encode_png(gray(image)), clock, observation_validator, policy=policy
    )
    assert len(observation["defects"]) == 5
    assert (
        observation["pipeline_identity"]["threshold_policy_version"]
        == "vision-tp-test-cap/1"
    )
    assert [d["defect_id"] for d in observation["defects"]] == [
        "D-1",
        "D-2",
        "D-3",
        "D-4",
        "D-5",
    ]


def test_naive_clock_is_rejected() -> None:
    from datetime import datetime

    data = encode_png(gray(textured()))
    ref = reference_for(data)
    work = parse_request(request_for(ref))
    with pytest.raises(ValueError, match="aware UTC"):
        inspect(
            work,
            store_with(ref, data),
            observation_id=OBSERVATION_ID,
            clock=lambda: datetime(2026, 10, 25, 9, 0, 0),
        )
