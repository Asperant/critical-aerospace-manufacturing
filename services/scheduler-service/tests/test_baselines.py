"""BaselineDefinition coverage: exactly SCH-B1..SCH-B5 with complete metadata."""

from __future__ import annotations

import dataclasses

import manufacturing_scheduler
import pytest
from manufacturing_scheduler import (
    BASELINES,
    POLICIES,
    BaselineStrength,
    FreezeStatus,
    LifecycleState,
    NotApplicable,
    UnsupportedPolicyError,
    get_baseline,
)

# docs/01 "BaselineDefinition Metadata" (Item 14), one entry per minimum field,
# mapped to the record field that carries it. Written out, not derived.
CANONICAL_FIELDS = {
    "BaselineID": "baseline_id",
    "BaselineFamily": "baseline_family",
    "ResearchQuestionIDs": "research_question_ids",
    "ComparatorClass": "comparator_class",
    "BaselineStrength": "baseline_strength",
    "method description": "method_description",
    "implementation version": "implementation_version",
    "Git SHA": "git_sha",
    "information/evidence access": "information_access",
    "training DatasetVersions": "training_datasets",
    "preprocessing": "preprocessing",
    "output contract": "output_contract",
    "hyperparameters": "hyperparameters",
    "TuningProtocol": "tuning_protocol",
    "compute/resource budget": "compute_budget",
    "API/token budget": "api_token_budget",
    "seed policy": "seed_policy",
    "failure policy": "failure_policy",
    "references": "references",
    "limitations": "limitations",
    "freeze status": "freeze_status",
}


def test_exactly_the_five_canonical_baselines_exist() -> None:
    ids = ["SCH-B1", "SCH-B2", "SCH-B3", "SCH-B4", "SCH-B5"]
    assert list(BASELINES) == list(POLICIES) == ids
    assert {i: p.name for i, p in POLICIES.items()} == {
        "SCH-B1": "FIFO",
        "SCH-B2": "EDD",
        "SCH-B3": "CR",
        "SCH-B4": "SPT",
        "SCH-B5": "SRPT",
    }


def test_every_canonical_metadata_field_is_a_record_field() -> None:
    fields = {
        f.name for f in dataclasses.fields(manufacturing_scheduler.BaselineDefinition)
    }
    assert set(CANONICAL_FIELDS.values()) <= fields


@pytest.mark.parametrize("baseline_id", sorted(BASELINES))
def test_record_is_complete_and_honest_about_status(baseline_id: str) -> None:
    record = get_baseline(baseline_id)
    assert record.baseline_id == baseline_id
    for field in CANONICAL_FIELDS.values():
        value = getattr(record, field)
        if field != "git_sha":
            assert value, f"{baseline_id}.{field} is empty"
    assert record.research_question_ids == ("RQ-2",)
    assert record.implementation_version == POLICIES[baseline_id].version
    # Not resolved at definition time, and no research status is claimed.
    assert record.git_sha is None
    assert record.freeze_status is FreezeStatus.NOT_FROZEN
    assert record.lifecycle_state is LifecycleState.IMPLEMENTED
    assert isinstance(record.training_datasets, NotApplicable)
    assert isinstance(record.api_token_budget, NotApplicable)
    assert record.training_datasets.reason and record.api_token_budget.reason
    assert ("tie_break", "queue_entry_tick, then job_id") in record.hyperparameters


def test_comparator_classification_cites_the_canonical_text_only_where_it_exists() -> (
    None
):
    assert get_baseline("SCH-B1").comparator_class == "BC-2 Operational Baseline"
    srpt = get_baseline("SCH-B5")
    assert (srpt.comparator_class, srpt.baseline_strength) == (
        "BC-3 Strong Baseline",
        BaselineStrength.STRONG,
    )
    for baseline_id in ("SCH-B2", "SCH-B3", "SCH-B4"):
        assert "proposal" in get_baseline(baseline_id).strength_basis


def test_the_two_distinct_processing_time_rules_are_described_as_such() -> None:
    assert "next-operation" in get_baseline("SCH-B4").method_description
    assert "remaining-route" in get_baseline("SCH-B5").method_description


@pytest.mark.parametrize("bad", ["SCH-B0", "SCH-B6", "", None, 3])
def test_unknown_baseline_is_rejected(bad: object) -> None:
    with pytest.raises(UnsupportedPolicyError):
        get_baseline(bad)


def test_public_package_exposes_the_interface() -> None:
    for name in manufacturing_scheduler.__all__:
        assert hasattr(manufacturing_scheduler, name)
