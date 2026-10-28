"""WP-TEST-007: the architecture-boundary and trace checks are required CI gates.

A check that runs in a job `ci-gate` does not wait for is advisory, however green it
looks. This test reads .github/workflows/ci.yml and ci/required_checks.json and fails
when either check could be skipped, made non-blocking or left out of the gate
(TEST-ARCH-BOUNDARY, TEST-GOV-TRACELINT; CI, EV-L2).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text("utf-8"))
REQUIRED = json.loads((ROOT / "ci/required_checks.json").read_text("utf-8"))

# (job, step name prefix, command fragments that must all appear in its `run`)
GATE_STEPS = [
    ("static", "Architecture boundary rules", ["check_architecture_boundaries.py"]),
    (
        "unit",
        "Trace registry lint and tests",
        ["cap_trace validate --base origin/main", "cap_trace drift --strict"],
    ),
]


def find_step(job: str, prefix: str) -> dict[str, Any]:
    steps = [
        s
        for s in WORKFLOW["jobs"][job]["steps"]
        if s.get("name", "").startswith(prefix)
    ]
    assert (
        len(steps) == 1
    ), f"{job}: exactly one step '{prefix}...' expected, got {len(steps)}"
    return steps[0]


@pytest.mark.parametrize(("job", "prefix", "commands"), GATE_STEPS)
def test_the_check_runs_in_a_job_and_cannot_be_skipped(
    job: str, prefix: str, commands: list[str]
) -> None:
    step = find_step(job, prefix)
    for command in commands:
        assert command in step["run"], f"{prefix}: missing '{command}'"
    assert "if" not in step, f"{prefix}: a conditional step can be skipped silently"
    assert not step.get("continue-on-error"), f"{prefix}: must not be non-blocking"
    assert "||" not in step["run"], f"{prefix}: '||' would swallow its exit status"
    assert not WORKFLOW["jobs"][job].get("continue-on-error"), f"{job} is non-blocking"
    assert "if" not in WORKFLOW["jobs"][job], f"{job} can be skipped"


def test_pull_requests_also_run_the_requirement_impact_check() -> None:
    step = find_step("unit", "PR Requirement-Impact")
    assert step["if"] == "github.event_name == 'pull_request'"
    assert "cap_trace impact" in step["run"] and not step.get("continue-on-error")


def test_ci_gate_waits_for_the_jobs_that_hold_the_checks() -> None:
    gate = WORKFLOW["jobs"]["gate"]
    assert gate["name"] == "ci-gate" and gate["if"] == "always()"
    for job, _, _ in GATE_STEPS:
        assert job in gate["needs"], f"ci-gate does not wait for {job}"
    script = next(s["run"] for s in gate["steps"] if "run" in s)
    assert (
        'expected = {"scope", "static", "unit", "contract"}' in script
    ), "ci-gate no longer requires static and unit on every event"
    assert 'needs[k]["result"] != "success"' in script


def test_ci_gate_is_a_required_status_check_on_main() -> None:
    assert "ci-gate" in REQUIRED["required_status_checks"]
    assert REQUIRED["strict"] is True and REQUIRED["enforce_admins"] is True
    assert REQUIRED["required_approving_review_count"] == 0
