"""Vision's consumed view of an inspection request (IC-VIS-001).

IC-VIS-001 is owned by its producer and its exact schema is not frozen yet
(02 marks the field list as derived candidates). This module accepts only the
fields Vision needs and rejects every other field, so Oracle or evaluator labels
cannot enter the inference path by accident. It is not a published contract.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

from cap_artifacts import ArtifactReference, InvalidReferenceError

OPAQUE = re.compile(r"^\S{1,128}$")
FIELDS = frozenset(
    {"inspection_request_id", "inspection_run_id", "world_id", "subject", "artifact"}
)
SUBJECT_FIELDS = frozenset(
    {
        "lot_id",
        "lot_revision",
        "serialized_component_id",
        "serialized_component_revision",
        "route_visit_id",
    }
)
IMAGE_TYPE = "inspection_image"


class RequestError(ValueError):
    """The request is malformed or outside Vision's accepted input; names fields only."""


@dataclass(frozen=True)
class Subject:
    lot_id: str
    lot_revision: str
    serialized_component_id: str
    serialized_component_revision: str
    route_visit_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "lot_id": self.lot_id,
            "lot_revision": self.lot_revision,
            "serialized_component_id": self.serialized_component_id,
            "serialized_component_revision": self.serialized_component_revision,
            "route_visit_id": self.route_visit_id,
        }


@dataclass(frozen=True)
class InspectionWork:
    inspection_request_id: str
    inspection_run_id: str
    world_id: str
    subject: Subject
    artifact: ArtifactReference


def _exact(value: object, allowed: frozenset[str], where: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RequestError(f"{where}: expected an object")
    mapping = cast(Mapping[object, object], value)
    keys = {str(key) for key in mapping}
    unknown = sorted(keys - allowed)
    missing = sorted(allowed - keys)
    if unknown:
        raise RequestError(f"{where}: unexpected fields {unknown}")
    if missing:
        raise RequestError(f"{where}: missing fields {missing}")
    return {str(key): item for key, item in mapping.items()}


def _opaque(data: Mapping[str, Any], field: str, where: str) -> str:
    value = data[field]
    if not isinstance(value, str) or not OPAQUE.fullmatch(value):
        raise RequestError(f"{where}{field}: expected an opaque nonblank identity")
    return value


def parse_request(value: object) -> InspectionWork:
    data = _exact(value, FIELDS, "request")
    subject_data = _exact(data["subject"], SUBJECT_FIELDS, "subject")
    subject = Subject(
        **{field: _opaque(subject_data, field, "subject/") for field in SUBJECT_FIELDS}
    )
    try:
        artifact = ArtifactReference.from_dict(data["artifact"])
    except InvalidReferenceError:
        raise RequestError("artifact: invalid cap.artifact-ref/v1 reference") from None
    world_id = _opaque(data, "world_id", "")
    if artifact.data["artifact_type"] != IMAGE_TYPE:
        raise RequestError(f"artifact/artifact_type: expected {IMAGE_TYPE}")
    if artifact.data["classification"] == "RESTRICTED_ORACLE":
        raise RequestError(
            "artifact/classification: Oracle artifacts are not Vision input"
        )
    if artifact.data["context"]["world_id"] != world_id:
        raise RequestError("world_id: does not match the artifact context")
    return InspectionWork(
        inspection_request_id=_opaque(data, "inspection_request_id", ""),
        inspection_run_id=_opaque(data, "inspection_run_id", ""),
        world_id=world_id,
        subject=subject,
        artifact=artifact,
    )
