"""TEST-EVT-SCHEMA: Vision InspectionObservation v1 payload contract (WP-VIS-001).

Producer/consumer boundary test over the registered declaration and its
SYNTHETIC TEST fixtures, plus the cross-contract identities consumed from
core.order-query.v1 and cap.artifact-ref/v1. No broker, artifact fetch or
inference is exercised here.
"""

import copy
import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from cap_contracts import (
    BoundaryValidator,
    ContractViolation,
    ProducerAuthorities,
    Registry,
)

REPO = Path(__file__).resolve().parents[2]
REGISTRY = Registry.load(REPO / "packages/contracts/registry")
AUTHORITIES = ProducerAuthorities.load(
    REPO / "packages/contracts/producer-authorities.json"
)
CONTRACT_ID = "vision.inspection-observation.v1"
DECLARATION = REGISTRY.get(CONTRACT_ID)
CONTRACT_DIR = REPO / "services/vision-service/contracts/v1"
CORE_FIXTURE = (
    REPO / "services/manufacturing-core/contracts/v1/order-query.reentrant.json"
)
ARTIFACT_EXAMPLE = (
    REPO / "packages/artifacts/src/cap_artifacts/schemas/artifact-reference.json"
)
FIXTURES = (
    "inspection-observation.defect-candidates.json",
    "inspection-observation.no-defect-candidates.json",
    "inspection-observation.not-evaluated.json",
    "inspection-observation.degraded-input.json",
)
FORBIDDEN_FIELD_TOKENS = (
    "oracle",
    "ground_truth",
    "true_label",
    "disposition",
    "hold",
    "root_cause",
    "accept",
    "accepted",
    "acceptance",
)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fixture(name: str) -> dict[str, Any]:
    return load(CONTRACT_DIR / name)


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def semantic_errors(payload: dict[str, Any]) -> list[str]:
    """Rules JSON Schema cannot express; documented in the contract README."""
    errors: list[str] = []
    defect_ids = [defect["defect_id"] for defect in payload["defects"]]
    if len(defect_ids) != len(set(defect_ids)):
        errors.append("defects/defect_id: not unique")
    inference = payload["inference"]
    if instant(inference["completed_at"]) < instant(inference["started_at"]):
        errors.append("inference/completed_at: earlier than started_at")
    return errors


def rejected(payload: dict[str, Any]) -> None:
    validator = BoundaryValidator(DECLARATION, REPO)
    with pytest.raises(ContractViolation):
        validator.validate(payload, role="producer")
    with pytest.raises(ContractViolation):
        validator.validate(payload, role="consumer")


def property_names(node: object) -> set[str]:
    names: set[str] = set()
    if isinstance(node, dict):
        for key, value in cast(dict[str, object], node).items():
            if key == "properties" and isinstance(value, dict):
                names.update(cast(dict[str, object], value))
            names |= property_names(cast(object, value))
    elif isinstance(node, list):
        for item in cast(list[object], node):
            names |= property_names(item)
    return names


def test_declaration_is_registered_and_owned_by_vision() -> None:
    REGISTRY.verify_authorities(AUTHORITIES, repo_root=REPO)
    REGISTRY.verify(REPO)
    assert DECLARATION.contract_type == "EVENT"
    assert DECLARATION.sync_semantics == "ASYNC"
    assert DECLARATION.canonical_producer == "vision-service"
    assert DECLARATION.declared_consumers == (
        "AI/RCA evidence intake",
        "Digital Twin",
        "Core quality normalization",
    )
    assert tuple(ref.path.rsplit("/", 1)[1] for ref in DECLARATION.fixtures) == FIXTURES


@pytest.mark.parametrize("name", FIXTURES)
def test_producer_and_consumer_validate_the_same_fixture(name: str) -> None:
    validator = BoundaryValidator(DECLARATION, REPO)
    payload = fixture(name)
    validator.validate(payload, role="producer")
    validator.validate(payload, role="consumer")
    assert semantic_errors(payload) == []


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_subject_uses_existing_core_identities(name: str) -> None:
    core = load(CORE_FIXTURE)
    subject = fixture(name)["subject"]
    components = {component["id"]: component for component in core["components"]}
    lots = {lot["id"]: lot for lot in core["lots"]}
    component = components[subject["serialized_component_id"]]
    assert component["revision"] == subject["serialized_component_revision"]
    assert component["lot_id"] == subject["lot_id"]
    assert lots[subject["lot_id"]]["revision"] == subject["lot_revision"]
    assert subject["route_visit_id"] in {
        visit["id"] for visit in core["route"]["visits"]
    }


@pytest.mark.parametrize("name", FIXTURES)
def test_fixture_source_artifact_matches_artifact_reference(name: str) -> None:
    reference = load(ARTIFACT_EXAMPLE)
    payload = fixture(name)
    source = payload["source_artifact"]
    assert source["ref_schema"] == reference["schema"]
    assert {
        key: source[key] for key in ("artifact_id", "version", "artifact_type")
    } == {key: reference[key] for key in ("artifact_id", "version", "artifact_type")}
    assert source["checksum"] == reference["checksum"]
    assert payload["context"] == reference["context"]


def test_invalid_input_cannot_be_reported_as_no_defect() -> None:
    payload = fixture("inspection-observation.no-defect-candidates.json")
    payload["data_quality"] = {
        "status": "INVALID_INPUT",
        "flags": ["UNDECODABLE_IMAGE"],
    }
    rejected(payload)


def test_not_evaluated_requires_invalid_input_and_no_scores() -> None:
    payload = fixture("inspection-observation.not-evaluated.json")
    payload["data_quality"] = {"status": "VALID", "flags": []}
    rejected(payload)

    payload = fixture("inspection-observation.not-evaluated.json")
    payload["image_anomaly_score"] = 0.4
    rejected(payload)

    payload = fixture("inspection-observation.not-evaluated.json")
    payload["defects"] = copy.deepcopy(
        fixture("inspection-observation.defect-candidates.json")["defects"]
    )
    rejected(payload)


def test_outcome_must_agree_with_candidates() -> None:
    payload = fixture("inspection-observation.defect-candidates.json")
    payload["defects"] = []
    rejected(payload)

    payload = fixture("inspection-observation.defect-candidates.json")
    payload["outcome"] = "NO_DEFECT_CANDIDATES"
    rejected(payload)


def test_non_valid_data_quality_must_name_a_flag() -> None:
    payload = fixture("inspection-observation.degraded-input.json")
    payload["data_quality"]["flags"] = []
    rejected(payload)

    payload = fixture("inspection-observation.no-defect-candidates.json")
    payload["data_quality"]["flags"] = ["LOW_CONTRAST"]
    rejected(payload)


def test_open_set_label_rules() -> None:
    payload = fixture("inspection-observation.defect-candidates.json")
    payload["defects"][1]["class_label"] = "surface_scratch"
    rejected(payload)

    payload = fixture("inspection-observation.defect-candidates.json")
    payload["defects"][0]["class_label"] = None
    rejected(payload)


def test_uncertain_candidate_forces_review() -> None:
    payload = fixture("inspection-observation.defect-candidates.json")
    payload["review_required"] = False
    rejected(payload)

    payload = fixture("inspection-observation.defect-candidates.json")
    payload["defects"] = payload["defects"][:1]
    payload["review_required"] = False
    BoundaryValidator(DECLARATION, REPO).validate(payload, role="producer")


@pytest.mark.parametrize(
    ("path", "field", "value"),
    [
        ((), "oracle_label", "crack"),
        ((), "ground_truth", "crack"),
        ((), "quality_disposition", "REJECT"),
        ((), "material_hold_id", "MH-1"),
        ((), "root_cause", "tool_wear"),
        (("defects", 0), "true_label", "crack"),
        (("source_artifact",), "storage", {"bucket": "cap-artifacts-rc-b", "key": "k"}),
        (("source_artifact",), "signed_url", "https://example.invalid/x"),
    ],
)
def test_oracle_authority_and_transport_fields_are_rejected(
    path: tuple[str | int, ...], field: str, value: object
) -> None:
    payload = fixture("inspection-observation.defect-candidates.json")
    target: Any = payload
    for step in path:
        target = target[step]
    target[field] = value
    rejected(payload)


def test_pipeline_identity_is_mandatory() -> None:
    for field in (
        "models",
        "preprocessing_version",
        "threshold_policy_version",
        "output_schema_version",
    ):
        payload = fixture("inspection-observation.defect-candidates.json")
        del payload["pipeline_identity"][field]
        rejected(payload)

    payload = fixture("inspection-observation.defect-candidates.json")
    payload["pipeline_identity"]["models"] = []
    rejected(payload)

    payload = fixture("inspection-observation.defect-candidates.json")
    payload["pipeline_identity"]["output_schema_version"] = (
        "vision.inspection-observation.v2"
    )
    rejected(payload)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("context", "world_id"), None),
        (("subject", "serialized_component_id"), " "),
        (("subject", "lot_revision"), ""),
        (("defects", 0, "class_confidence"), 1.2),
        (("defects", 0, "localization", "width"), 0),
        (("source_artifact", "checksum", "algorithm"), "md5"),
        (("observation_id",), "not-a-uuid"),
    ],
)
def test_malformed_identity_and_scores_are_rejected(
    path: tuple[str | int, ...], value: object
) -> None:
    payload = fixture("inspection-observation.defect-candidates.json")
    target: Any = payload
    for step in path[:-1]:
        target = target[step]
    target[path[-1]] = value
    rejected(payload)


def test_semantic_rules_detect_duplicates_and_time_order() -> None:
    payload = fixture("inspection-observation.defect-candidates.json")
    payload["defects"][1]["defect_id"] = payload["defects"][0]["defect_id"]
    assert semantic_errors(payload) == ["defects/defect_id: not unique"]

    payload = fixture("inspection-observation.defect-candidates.json")
    payload["inference"]["completed_at"] = "2026-10-25T09:00:00Z"
    assert semantic_errors(payload) == [
        "inference/completed_at: earlier than started_at"
    ]


def has_word_sequence(name: str, token: str) -> bool:
    """Match whole snake_case words, so threshold_policy_version is not a hold."""
    words, wanted = name.split("_"), token.split("_")
    return any(
        words[start : start + len(wanted)] == wanted
        for start in range(len(words) - len(wanted) + 1)
    )


def test_schema_declares_no_oracle_or_authority_fields() -> None:
    schema = load(REPO / DECLARATION.output_schema.path)
    names = property_names(schema)
    assert "threshold_policy_version" in names
    assert [
        name
        for name in names
        if any(has_word_sequence(name, token) for token in FORBIDDEN_FIELD_TOKENS)
    ] == []
    assert has_word_sequence("material_hold_id", "hold")
    assert has_word_sequence("oracle_label", "oracle")
