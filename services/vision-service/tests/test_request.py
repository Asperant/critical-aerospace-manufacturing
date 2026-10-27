"""TEST-VIS-PIPELINE: Vision's consumed request view accepts only allowlisted input."""

import copy
from typing import Any

import numpy as np
import pytest
from conftest import encode_png, reference_for, request_for
from vision_service import RequestError, parse_request

IMAGE = encode_png(np.zeros((16, 16, 1), dtype=np.uint8))


def valid() -> dict[str, Any]:
    return request_for(reference_for(IMAGE))


def test_valid_request_is_parsed_without_rewriting_identities() -> None:
    work = parse_request(valid())
    assert work.subject.serialized_component_id == "C-REENTRANT-1"
    assert work.subject.route_visit_id == "V-10"
    assert work.world_id == "world-dev-001"
    assert work.artifact.data["checksum"] == reference_for(IMAGE)["checksum"]


@pytest.mark.parametrize(
    "field", ["oracle_label", "ground_truth", "defect_class", "scenario_id"]
)
def test_unknown_request_fields_are_rejected(field: str) -> None:
    request = valid()
    request[field] = "crack"
    with pytest.raises(RequestError, match="unexpected fields"):
        parse_request(request)


def test_unknown_subject_fields_and_missing_fields_are_rejected() -> None:
    request = valid()
    request["subject"]["true_label"] = "crack"
    with pytest.raises(RequestError, match="subject: unexpected"):
        parse_request(request)

    request = valid()
    del request["subject"]["route_visit_id"]
    with pytest.raises(RequestError, match="subject: missing"):
        parse_request(request)

    request = valid()
    del request["artifact"]
    with pytest.raises(RequestError, match="request: missing"):
        parse_request(request)


@pytest.mark.parametrize("value", ["", " ", "a b", 7, None, "x" * 129])
def test_identities_must_be_opaque_nonblank_strings(value: object) -> None:
    request = valid()
    request["subject"]["lot_revision"] = value
    with pytest.raises(RequestError, match="lot_revision"):
        parse_request(request)


def test_world_must_match_the_artifact_context() -> None:
    with pytest.raises(RequestError, match="world_id"):
        parse_request(request_for(reference_for(IMAGE), world_id="world-other"))


def test_only_non_oracle_inspection_images_are_accepted() -> None:
    mask = reference_for(IMAGE, artifact_type="inspection_mask")
    mask["storage"]["key"] = mask["storage"]["key"].replace(
        "inspection_image", "inspection_mask"
    )
    with pytest.raises(RequestError, match="artifact_type"):
        parse_request(request_for(mask))
    with pytest.raises(RequestError, match="Oracle"):
        parse_request(
            request_for(reference_for(IMAGE, classification="RESTRICTED_ORACLE"))
        )


def test_invalid_artifact_reference_is_rejected() -> None:
    request = valid()
    broken = copy.deepcopy(request["artifact"])
    broken["storage"]["key"] = "lots/L-REENTRANT-2/image.png"
    request["artifact"] = broken
    with pytest.raises(RequestError, match="artifact: invalid"):
        parse_request(request)

    request = valid()
    request["subject"] = ["not", "an", "object"]
    with pytest.raises(RequestError, match="expected an object"):
        parse_request(request)
