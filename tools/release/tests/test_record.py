"""TEST-CICD-002-003 (part): the DeploymentRecord cannot claim more than its stages show."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from cap_release.record import STAGES, validate_record

COMMIT = "a" * 40


def record(**changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "schema": "cap.deployment-record/v1",
        "record_id": "DEP-REC-20261028T120000Z-0123abcd",
        "release_id": f"REL-{COMMIT[:12]}-1",
        "manifest_sha256": "f" * 64,
        "environment": {"id": "integration", "class": "INTEGRATION"},
        "host_source": {
            "checked_out_commit": COMMIT,
            "release_commit": COMMIT,
            "manual_patches": 0,
        },
        "supply_chain_verification": {
            "main_derived": True,
            "ci_gate": "success",
            "digests_in_registry": True,
            "tags_trusted": False,
        },
        "stages": [
            {
                "stage": s,
                "result": "PASSED",
                "started_at": "t",
                "finished_at": "t",
                "detail": "ok",
            }
            for s in STAGES
        ],
        "result": "SUCCEEDED",
        "previous_release_id": None,
        "rollback": None,
        "started_at": "t",
        "finished_at": "t",
    }
    base.update(changes)
    return base


def stages(**results: str) -> list[dict[str, Any]]:
    rows = copy.deepcopy(record()["stages"])
    for row in rows:
        row["result"] = results.get(row["stage"], "PASSED")
    return rows


def test_a_fully_passed_deployment_is_consistent() -> None:
    assert validate_record(record()) == []


def test_migrate_may_be_skipped_only_when_the_release_binds_no_schema() -> None:
    skipped = record(stages=stages(migrate="SKIPPED"))
    unbound = {
        "database_schema_target": {"state": "NOT_YET_PRODUCED", "reason": "x"},
        "release_id": skipped["release_id"],
    }
    bound = {
        "database_schema_target": {"state": "BOUND", "identity": "core:0001"},
        "release_id": skipped["release_id"],
    }
    assert validate_record(skipped, unbound) == []
    assert any("migrate" in p for p in validate_record(skipped, bound))


@pytest.mark.parametrize("failed", [s for s in STAGES if s != "migrate"])
def test_succeeded_needs_every_stage_passed(failed: str) -> None:
    problems = validate_record(record(stages=stages(**{failed: "FAILED"})))
    assert any(f"stage {failed}" in p for p in problems), problems


def test_a_stage_that_was_not_run_cannot_sit_in_a_succeeded_record() -> None:
    assert validate_record(record(stages=stages(smoke="NOT_RUN")))


def test_failed_and_rolled_back_must_show_a_stage_that_did_not_pass() -> None:
    assert any(
        "every stage passed" in p for p in validate_record(record(result="FAILED"))
    )
    assert any(
        "every stage passed" in p for p in validate_record(record(result="ROLLED_BACK"))
    )


def test_a_stage_cannot_run_after_the_deployment_stopped() -> None:
    problems = validate_record(record(result="FAILED", stages=stages(rollout="FAILED")))
    assert any("ran after an earlier stage stopped" in p for p in problems)


@pytest.mark.parametrize(
    ("changes", "expect"),
    [
        (
            {
                "host_source": {
                    "checked_out_commit": COMMIT,
                    "release_commit": COMMIT,
                    "manual_patches": 2,
                }
            },
            "zero manual source patches",
        ),
        (
            {
                "host_source": {
                    "checked_out_commit": "b" * 40,
                    "release_commit": COMMIT,
                    "manual_patches": 0,
                }
            },
            "equal the release commit",
        ),
        (
            {
                "supply_chain_verification": {
                    "main_derived": False,
                    "ci_gate": "success",
                    "digests_in_registry": True,
                    "tags_trusted": False,
                }
            },
            "main-derived",
        ),
        (
            {
                "supply_chain_verification": {
                    "main_derived": True,
                    "ci_gate": "failure",
                    "digests_in_registry": True,
                    "tags_trusted": False,
                }
            },
            "green ci-gate",
        ),
        (
            {
                "supply_chain_verification": {
                    "main_derived": True,
                    "ci_gate": "success",
                    "digests_in_registry": False,
                    "tags_trusted": False,
                }
            },
            "digests present",
        ),
        (
            {
                "supply_chain_verification": {
                    "main_derived": True,
                    "ci_gate": "success",
                    "digests_in_registry": True,
                    "tags_trusted": True,
                }
            },
            "tags_trusted",
        ),
        ({"result": "DONE"}, "result"),
        ({"stages": record()["stages"][:4]}, "stages"),
        ({"record_id": "x"}, "record_id"),
        ({"extra": 1}, "extra"),
    ],
)
def test_a_succeeded_record_that_overclaims_is_rejected(
    changes: dict[str, Any], expect: str
) -> None:
    problems = validate_record(record(**changes))
    assert any(expect in p for p in problems), problems


def test_stages_must_be_the_five_in_order() -> None:
    rows = record()["stages"]
    assert any(
        "in order" in p
        for p in validate_record(record(stages=[rows[1], rows[0], *rows[2:]]))
    )


def test_the_record_must_name_the_release_of_its_manifest() -> None:
    assert any(
        "differs from the manifest" in p
        for p in validate_record(record(), {"release_id": "REL-other-1"})
    )
