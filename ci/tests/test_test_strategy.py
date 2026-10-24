"""Negative and positive paths of the test-strategy check (WP-TEST-001, TEST-TEST-001-001)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from check_test_strategy import (
    REPO_ROOT,
    Inputs,
    check,
    find_test_files,
    load,
    owning_suite,
)


def base_strategy() -> dict[str, Any]:
    return {
        "schema": "cap.test-strategy/v1",
        "boundary_modes": ["REAL", "FIXTURE_ALLOWED", "STUB_ALLOWED", "MOCK_ONLY"],
        "tiers": [
            {
                "name": "unit",
                "purpose": "u",
                "ci_job": "unit",
                "budget_s": 1,
                "boundary_modes": ["FIXTURE_ALLOWED", "STUB_ALLOWED", "MOCK_ONLY"],
            },
            {
                "name": "integration",
                "purpose": "i",
                "ci_job": "integration",
                "budget_s": 1,
                "boundary_modes": ["REAL", "FIXTURE_ALLOWED"],
            },
            {
                "name": "benchmark",
                "purpose": "b",
                "ci_job": None,
                "budget_s": 1,
                "boundary_modes": ["REAL"],
            },
        ],
        "test_id": {
            "pattern": "^TEST-[A-Z]+-[0-9]{3}-[0-9]{3}$",
            "rule": "r",
            "legacy": ["TEST-CICD-001"],
        },
        "suites": [
            {
                "path": "pkg/tests",
                "owner": "Yavuz",
                "work_package": "WP-ABC-001",
                "families": ["TEST-ABC-FAMILY"],
                "test_ids": ["TEST-ABC-001-001"],
                "runs": [
                    {
                        "tier": "unit",
                        "boundary_mode": "FIXTURE_ALLOWED",
                        "ci_step": "Unit",
                    },
                    {
                        "tier": "integration",
                        "boundary_mode": "REAL",
                        "ci_step": "Integ",
                    },
                ],
            },
        ],
    }


def inputs(strategy: dict[str, Any], files: list[str] | None = None) -> Inputs:
    return Inputs(
        strategy=strategy,
        steps={
            "Unit": ("unit", "pytest pkg/tests -m 'not integration'"),
            "Integ": ("integration", "pytest pkg/tests -m integration"),
            "Other": ("unit", "pytest other/tests"),
        },
        families={"TEST-ABC-FAMILY"},
        work_packages={"WP-ABC-001"},
        test_files=files if files is not None else ["pkg/tests/test_a.py"],
    )


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "pkg/tests").mkdir(parents=True)
    (tmp_path / "pkg/tests/test_a.py").write_text("")
    return tmp_path


def violations(
    strategy: dict[str, Any], root: Path, files: list[str] | None = None
) -> list[str]:
    return check(inputs(strategy, files), root).violations


def test_conforming_strategy_passes(root: Path) -> None:
    assert violations(base_strategy(), root) == []


def test_untracked_test_file_fails(root: Path) -> None:
    found = violations(
        base_strategy(), root, ["pkg/tests/test_a.py", "new/tests/test_b.py"]
    )
    assert any(
        "new/tests/test_b.py: test file belongs to no declared suite" in v
        for v in found
    )


def mutate(run: int | None, key: str, value: object) -> dict[str, Any]:
    strategy = copy.deepcopy(base_strategy())
    suite: dict[str, Any] = strategy["suites"][0]
    target: dict[str, Any] = suite if run is None else suite["runs"][run]
    target[key] = value
    return strategy


@pytest.mark.parametrize(
    ("run", "key", "value", "expected"),
    [
        (0, "ci_step", "Missing", "not found"),
        (0, "ci_step", "Integ", "is in job integration"),
        (0, "ci_step", "Other", "does not execute this path"),
        (1, "boundary_mode", "MOCK_ONLY", "not allowed in tier integration"),
        (1, "boundary_mode", "FIXTURE_ALLOWED", "must name fixture_boundaries"),
        (None, "families", ["TEST-NOPE"], "not declared in 03"),
        (None, "families", [], "no family_note"),
        (None, "test_ids", ["TEST-ABC-1"], "breaks"),
        (None, "test_ids", ["TEST-XYZ-009-001"], "unknown WP-XYZ-009"),
        (None, "test_ids", ["TEST-ABC-001-001", "TEST-ABC-001-001"], "declared twice"),
        (None, "work_package", "WP-NOPE-001", "not a work package in 04"),
        (None, "path", "missing/tests", "suite path does not exist"),
        (0, "ci_step", None, "no on_request explanation"),
    ],
)
def test_violations_are_reported(
    root: Path, run: int | None, key: str, value: object, expected: str
) -> None:
    found = violations(mutate(run, key, value), root)
    assert any(expected in v for v in found), found


def test_legacy_ids_and_on_request_runs_are_accepted(root: Path) -> None:
    strategy = mutate(None, "test_ids", ["TEST-CICD-001"])
    runs: list[dict[str, Any]] = strategy["suites"][0]["runs"]
    runs.append(
        {
            "tier": "benchmark",
            "boundary_mode": "REAL",
            "ci_step": None,
            "on_request": "BENCH=1",
        }
    )
    assert violations(strategy, root) == []


def test_most_specific_suite_owns_the_file() -> None:
    paths = ["web/e2e", "web/e2e/bench.spec.ts", "web"]
    assert owning_suite("web/e2e/bench.spec.ts", paths) == "web/e2e/bench.spec.ts"
    assert owning_suite("web/e2e/a.spec.ts", paths) == "web/e2e"
    assert owning_suite("webapp/x.test.ts", paths) is None


def test_discovery_skips_dependencies(tmp_path: Path) -> None:
    for name in [
        "a/test_x.py",
        "a/.venv/lib/test_y.py",
        "b/node_modules/z.test.ts",
        "c/u.spec.ts",
        "c/helper.py",
    ]:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("")
    assert find_test_files(tmp_path) == ["a/test_x.py", "c/u.spec.ts"]


def test_repository_strategy_conforms() -> None:
    result = check(load(REPO_ROOT), REPO_ROOT)
    assert result.violations == [], result.violations
    assert result.files > 0
