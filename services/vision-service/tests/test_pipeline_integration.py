"""TEST-VIS-PIPELINE against REAL SeaweedFS (WP-VIS-001, TEST-VIS-001-003).

Runs in t1-integration after `infra/compose/stack.sh up infra`, with the
environment from `stack.sh env`. Missing infrastructure fails, it never skips.
The image is written with the writer identity and read back by the pipeline with
the reader identity; every run uses fresh artifact identities.
"""

from __future__ import annotations

import copy
import os
from collections.abc import Iterator
from typing import Any

import pytest
from cap_artifacts import ArtifactStore, IntegrityError, S3Client, StoreConfig
from cap_contracts import BoundaryValidator
from conftest import encode_png, gray, request_for, textured
from vision_service import inspect, parse_request

pytestmark = pytest.mark.integration

CONTEXT = {
    "world_id": "world-it-vision",
    "simulation_run_id": "run-it-1",
    "branch_id": None,
}
OBSERVATION_ID = "1b2c3d4e-5f60-4a71-8b92-a3b4c5d6e7f8"


def _client(role: str) -> S3Client:
    if not os.environ.get("CAP_S3_ENDPOINT"):
        pytest.fail(
            "CAP_S3_ENDPOINT not set: start the infra profile (infra/compose/stack.sh up infra)"
        )
    return S3Client(StoreConfig.from_env(role=role))


@pytest.fixture(scope="module")
def stores() -> Iterator[tuple[ArtifactStore, ArtifactStore]]:
    admin = _client("admin")
    ArtifactStore(admin).ensure_buckets()
    admin.close()
    writer, reader = _client("writer"), _client("reader")
    yield ArtifactStore(writer), ArtifactStore(reader)
    writer.close()
    reader.close()


def stored_image(writer: ArtifactStore) -> dict[str, Any]:
    image = textured(seed=11)
    image[10:14, 40:47] = 1.0
    ref = writer.store(
        encode_png(gray(image)),
        artifact_type="inspection_image",
        artifact_class="OPERATIONAL_EVIDENCE",
        retention_class="RC-B",
        content_type="image/png",
        format_version="png/1",
        logical_owner="vision-service",
        producer={"service": "vision-integration-test", "version": "0.1.0"},
        classification="INTERNAL",
        context=CONTEXT,
        provenance={
            "source_artifacts": [],
            "source_refs": ["inspection_request:IR-IT-1"],
        },
    )
    return ref.to_dict()


def test_pipeline_reads_real_object_storage_and_publishes_a_valid_observation(
    stores: tuple[ArtifactStore, ArtifactStore],
    clock: Any,
    observation_validator: BoundaryValidator,
) -> None:
    writer, reader = stores
    ref = stored_image(writer)
    work = parse_request(request_for(ref))
    observation = inspect(work, reader, observation_id=OBSERVATION_ID, clock=clock)
    observation_validator.validate(observation, role="producer")
    observation_validator.validate(observation, role="consumer")
    assert observation["outcome"] == "DEFECT_CANDIDATES"
    assert observation["source_artifact"]["artifact_id"] == ref["artifact_id"]
    assert observation["source_artifact"]["checksum"] == ref["checksum"]
    assert observation["context"] == CONTEXT
    box = observation["defects"][0]["localization"]
    assert (box["x"], box["y"]) == (40 / 64, 10 / 64)


def test_reference_with_a_foreign_checksum_is_refused_by_the_real_read(
    stores: tuple[ArtifactStore, ArtifactStore], clock: Any
) -> None:
    writer, reader = stores
    ref = stored_image(writer)
    forged = copy.deepcopy(ref)
    forged["checksum"]["value"] = "0" * 64
    work = parse_request(request_for(forged))
    with pytest.raises(IntegrityError):
        inspect(work, reader, observation_id=OBSERVATION_ID, clock=clock)
