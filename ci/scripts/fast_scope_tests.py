"""Run bounded, changed-scope regression tests for the PR required gate."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT = 90
PYTEST = ["uv", "run", "--project", "ci", "--locked", "python", "-m", "pytest"]


def changed_paths() -> list[str]:
    base = os.environ.get("FAST_GATE_BASE")
    if not base:
        raise SystemExit("FAST_GATE_BASE is required for pull-request scope selection")
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def run(label: str, command: list[str]) -> None:
    print(f"FAST_SCOPE {label}: {' '.join(command)}", flush=True)
    subprocess.run(
        ["timeout", "--signal=TERM", str(TIMEOUT), *command], cwd=ROOT, check=True
    )


def main() -> int:
    paths = changed_paths()
    selected: list[tuple[str, list[str]]] = []

    if any(path.startswith("tools/host/plane-queue/") for path in paths):
        selected.append(
            (
                "plane-queue",
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tools/host/plane-queue",
                    "-p",
                    "test_*.py",
                ],
            )
        )
    if any(path.startswith("tools/host/plane-transition/") for path in paths):
        selected.append(
            (
                "plane-transition",
                [
                    sys.executable,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tools/host/plane-transition",
                    "-p",
                    "test_*.py",
                ],
            )
        )
    if any(
        path.startswith("tools/projectctl/src/projectctl/execution_queue.py")
        for path in paths
    ):
        selected.append(
            (
                "projectctl-execution-queue",
                [
                    *PYTEST,
                    "tools/projectctl/tests/test_execution_queue.py",
                    "tools/projectctl/tests/test_health.py",
                    "-q",
                ],
            )
        )
    elif any(path.startswith("tools/projectctl/") for path in paths):
        selected.append(
            (
                "projectctl-focused",
                [
                    *PYTEST,
                    "tools/projectctl/tests/test_cli.py",
                    "tools/projectctl/tests/test_project.py",
                    "-q",
                ],
            )
        )
    if any(
        path.startswith("ci/") or path.startswith(".github/workflows/")
        for path in paths
    ):
        selected.append(
            (
                "ci-policy",
                [
                    *PYTEST,
                    "ci/tests/test_test_strategy.py",
                    "ci/tests/test_contract_ci_gate.py",
                    "-q",
                ],
            )
        )
    if any(path.startswith("packages/contracts/") for path in paths):
        selected.append(("contracts", ["python", "ci/scripts/check_contracts.py"]))

    if not selected:
        print(
            "FAST_SCOPE no specialized test family; canonical validation remains required"
        )
    for label, command in selected:
        run(label, command)
    print(f"FAST_SCOPE selected={len(selected)} changed_files={len(paths)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
