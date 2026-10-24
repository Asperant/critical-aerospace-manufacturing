"""Enforce the test strategy (WP-TEST-001) against the repository and CI workflow.

    uv run --project ci --locked python ci/scripts/check_test_strategy.py

`ci/test-strategy.json` (`cap.test-strategy/v1`) declares the test tiers with
their CI job and allowed boundary modes, the TestID convention, and every test
suite of the repository. This check fails when:

* a test file belongs to no declared suite (an untracked suite never runs by
  design, so it would silently escape every gate);
* a suite's run names a CI step that is missing, sits in a different job than
  its tier, or does not execute the suite's path;
* a run's boundary mode is not allowed for its tier, or a FIXTURE_ALLOWED
  integration run does not name the boundaries it replaces;
* a declared family does not exist in 03, or a suite without families gives no
  reason;
* a TestID breaks the convention, names a work package that does not exist in
  04, or is declared twice.

Exit 0 when everything conforms, 1 on violations, 2 when inputs are unreadable.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
STRATEGY = "ci/test-strategy.json"
WORKFLOW = ".github/workflows/ci.yml"
RTM = "docs/03_Requirements_Traceability_Matrix.md"
WBS = "docs/04_Work_Breakdown_Structure.md"
TEST_FILE = re.compile(r"(^test_.*\.py$|.*_test\.py$|.*\.(spec|test)\.tsx?$)")
SKIP_DIRS = {".venv", "node_modules", "dist", "__pycache__", ".git", ".pytest_cache"}
FAMILY_ROW = re.compile(
    r"^\| ((?:TEST|BENCH|INSP|RES|AV|DEMO|E2E)-[A-Z0-9-]+) \|", re.M
)
WP_HEADING = re.compile(r"^#### (WP-[A-Z]+-[0-9]{3}) ", re.M)


@dataclass
class Inputs:
    strategy: dict[str, Any]
    steps: dict[str, tuple[str, str]]  # step name -> (job id, run + working-directory)
    families: set[str]
    work_packages: set[str]
    test_files: list[str]


@dataclass
class Result:
    violations: list[str] = field(default_factory=list)
    suites: int = 0
    files: int = 0

    def fail(self, message: str) -> None:
        self.violations.append(message)


def workflow_steps(workflow: dict[str, Any]) -> dict[str, tuple[str, str]]:
    steps: dict[str, tuple[str, str]] = {}
    jobs = cast(dict[str, Any], workflow.get("jobs") or {})
    for job_id, job in jobs.items():
        job_steps = cast(
            list[dict[str, Any]], cast(dict[str, Any], job).get("steps") or []
        )
        for step in job_steps:
            name = step.get("name")
            if isinstance(name, str):
                text = f"{step.get('run', '')}\n{step.get('working-directory', '')}"
                steps[name] = (job_id, text)
    return steps


def find_test_files(root: Path) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.is_file() and TEST_FILE.match(path.name):
            found.append(rel.as_posix())
    return sorted(found)


def load(root: Path = REPO_ROOT) -> Inputs:
    strategy = json.loads((root / STRATEGY).read_text("utf-8"))
    workflow = yaml.safe_load((root / WORKFLOW).read_text("utf-8"))
    return Inputs(
        strategy=strategy,
        steps=workflow_steps(workflow),
        families=set(FAMILY_ROW.findall((root / RTM).read_text("utf-8"))),
        work_packages=set(WP_HEADING.findall((root / WBS).read_text("utf-8"))),
        test_files=find_test_files(root),
    )


def owning_suite(file: str, paths: list[str]) -> str | None:
    """The most specific declared suite path that contains the file."""
    matches = [p for p in paths if file == p or file.startswith(p.rstrip("/") + "/")]
    return max(matches, key=len) if matches else None


def check(inputs: Inputs, root: Path = REPO_ROOT) -> Result:
    result = Result()
    strategy = inputs.strategy
    tiers = {t["name"]: t for t in strategy["tiers"]}
    pattern = re.compile(strategy["test_id"]["pattern"])
    legacy = set(strategy["test_id"]["legacy"])
    suites = strategy["suites"]
    paths = [s["path"] for s in suites]
    result.suites = len(suites)

    if len(set(paths)) != len(paths):
        result.fail("suite paths must be unique")
    seen_ids: set[str] = set()
    for suite in suites:
        path = suite["path"]
        if not (root / path).exists():
            result.fail(f"{path}: suite path does not exist")
        wp = suite.get("work_package")
        if wp is not None and wp not in inputs.work_packages:
            result.fail(f"{path}: {wp} is not a work package in 04")
        families = suite.get("families", [])
        for family in families:
            if family not in inputs.families:
                result.fail(f"{path}: family {family} is not declared in 03")
        if not families and not suite.get("family_note"):
            result.fail(f"{path}: no 03 family and no family_note explaining why")
        for test_id in suite.get("test_ids", []):
            if test_id in seen_ids:
                result.fail(f"{path}: TestID {test_id} declared twice")
            seen_ids.add(test_id)
            if test_id in legacy:
                continue
            if not pattern.match(test_id):
                result.fail(f"{path}: TestID {test_id} breaks {pattern.pattern}")
                continue
            producer = "WP-" + "-".join(test_id.split("-")[1:3])
            if producer not in inputs.work_packages:
                result.fail(f"{path}: TestID {test_id} names unknown {producer}")
        for run in suite["runs"]:
            tier = tiers.get(run["tier"])
            if tier is None:
                result.fail(f"{path}: unknown tier {run['tier']}")
                continue
            mode = run["boundary_mode"]
            if mode not in tier["boundary_modes"]:
                result.fail(
                    f"{path}: boundary mode {mode} is not allowed in tier {tier['name']} "
                    f"(allowed: {', '.join(tier['boundary_modes'])})"
                )
            if (
                tier["name"] == "integration"
                and mode == "FIXTURE_ALLOWED"
                and not run.get("fixture_boundaries")
            ):
                result.fail(
                    f"{path}: FIXTURE_ALLOWED integration must name fixture_boundaries"
                )
            step = run["ci_step"]
            if step is None:
                if not run.get("on_request"):
                    result.fail(f"{path}: no CI step and no on_request explanation")
                continue
            if step not in inputs.steps:
                result.fail(f"{path}: CI step {step!r} not found in {WORKFLOW}")
                continue
            job, text = inputs.steps[step]
            if tier["ci_job"] != job:
                result.fail(
                    f"{path}: tier {tier['name']} runs in job {tier['ci_job']}, "
                    f"but step {step!r} is in job {job}"
                )
            executed = (
                path.rsplit("/", 1)[0] if "." in path.rsplit("/", 1)[-1] else path
            )
            parent = executed.split("/")[:2]
            if executed not in text and "/".join(parent) not in text:
                result.fail(f"{path}: step {step!r} does not execute this path")

    for file in inputs.test_files:
        result.files += 1
        if owning_suite(file, paths) is None:
            result.fail(f"{file}: test file belongs to no declared suite")
    return result


def main() -> int:
    try:
        inputs = load()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"cannot read test strategy inputs: {exc}", file=sys.stderr)
        return 2
    result = check(inputs)
    for violation in result.violations:
        print(f"VIOLATION {violation}")
    status = "FAIL" if result.violations else "PASS"
    print(
        f"{status}: test strategy covers {result.files} test files in {result.suites} suites; "
        f"{len(result.violations)} violation(s)"
    )
    return 1 if result.violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
