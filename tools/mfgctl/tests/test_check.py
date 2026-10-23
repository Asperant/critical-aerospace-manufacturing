from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from mfgctl.check import (
    WORKFLOW,
    WorkflowError,
    load_commands,
    render_summary,
    run_check,
)

REAL_ROOT = Path(__file__).resolve().parents[3]

WORKFLOW_TEXT = """
name: ci
jobs:
  static:
    name: t1-static
    steps:
      - uses: actions/checkout@v4
      - name: Sync locked CI toolchain
        run: uv sync --project ci --locked
      - name: Static ratchet
        run: uv run --project ci --locked python ci/scripts/static_ratchet.py check
  unit:
    name: t1-unit
    env:
      PYTHONPATH: ci:ci/scripts
    steps:
      - name: Queue tests
        run: uv run --project ci --locked python -m unittest discover -p 'test_*.py'
  contract:
    name: t1-contract
    steps:
      - name: Contracts
        run: uv run --project ci --locked python ci/scripts/check_contracts.py
"""


def write_workflow(root: Path, text: str = WORKFLOW_TEXT) -> Path:
    path = root / WORKFLOW
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return root


class FakeStream:
    def __init__(self, failing: set[str] | None = None) -> None:
        self.failing = failing or set()
        self.calls: list[tuple[tuple[str, ...], dict[str, str]]] = []

    def __call__(
        self, args: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> int:
        self.calls.append((tuple(args), dict(env)))
        return 1 if any(name in " ".join(args) for name in self.failing) else 0


def test_fast_tier_runs_only_static_uv_steps(tmp_path: Path) -> None:
    commands = load_commands(write_workflow(tmp_path), "fast")
    assert [c.name for c in commands] == ["Static ratchet"]
    assert commands[0].argv[:4] == ("uv", "run", "--project", "ci")


def test_pr_tier_keeps_job_environment_and_quoting(tmp_path: Path) -> None:
    commands = load_commands(write_workflow(tmp_path), "pr")
    assert [c.job for c in commands] == ["t1-static", "t1-unit", "t1-contract"]
    unit = commands[1]
    assert unit.env == {"PYTHONPATH": "ci:ci/scripts"}
    assert unit.argv[-2:] == ("-p", "test_*.py")


def test_missing_job_is_drift_not_a_silent_pass(tmp_path: Path) -> None:
    write_workflow(tmp_path, WORKFLOW_TEXT.split("  contract:")[0])
    with pytest.raises(WorkflowError, match="contract"):
        load_commands(tmp_path, "pr")


def test_job_without_uv_steps_is_drift(tmp_path: Path) -> None:
    text = WORKFLOW_TEXT.replace(
        "run: uv run --project ci --locked python ci/scripts/check_contracts.py",
        "run: echo contracts moved elsewhere",
    )
    with pytest.raises(WorkflowError, match="no uv run steps"):
        load_commands(write_workflow(tmp_path, text), "pr")


def test_unreadable_workflow_and_unknown_tier(tmp_path: Path) -> None:
    with pytest.raises(WorkflowError, match="cannot read"):
        load_commands(tmp_path, "fast")
    with pytest.raises(WorkflowError, match="unknown tier"):
        load_commands(write_workflow(tmp_path), "everything")


def test_run_reports_every_step_and_fails_on_any_failure(tmp_path: Path) -> None:
    root = write_workflow(tmp_path)
    commands = load_commands(root, "pr")
    stream = FakeStream(failing={"check_contracts"})
    ticks = iter(float(n) for n in range(100))
    announced: list[str] = []
    report = run_check(
        root, commands, "pr", stream, announced.append, lambda: next(ticks)
    )
    assert len(stream.calls) == 3  # keeps going after a failure, like CI jobs
    assert report.exit_code == 1
    assert announced[0].startswith("[1/3] t1-static")
    summary = render_summary(report)
    assert "FAIL    t1-contract" in summary
    assert "NOT RUN t1-integration" in summary
    assert summary.splitlines()[-1].startswith("Result: FAIL")


def test_all_green_passes(tmp_path: Path) -> None:
    root = write_workflow(tmp_path)
    report = run_check(root, load_commands(root, "fast"), "fast", FakeStream(), print)
    assert report.exit_code == 0
    assert "NOT RUN" not in render_summary(report)


def test_real_ci_workflow_still_provides_the_commands() -> None:
    """Guard against drift: the repository's own ci.yml must stay readable."""
    pr = load_commands(REAL_ROOT, "pr")
    names = {command.name for command in pr}
    assert "mfgctl tests (quarantine-aware)" in names
    assert {command.job for command in pr} == {"t1-static", "t1-unit", "t1-contract"}


MULTI_LINE = """
jobs:
  static:
    name: t1-static
    steps:
      - name: Ratchet
        run: uv run --project ci python ratchet.py
  unit:
    name: t1-unit
    steps:
      - name: Core tests and typing
        run: |
          uv run --project ci --locked python -m pytest services/core/tests -m 'not integration'
          uv run --project ci --locked pyright --project services/core/pyrightconfig.json
  contract:
    name: t1-contract
    steps:
      - name: Contracts
        run: uv run --project ci python contracts.py
"""


def test_multi_line_step_runs_each_line(tmp_path: Path) -> None:
    commands = load_commands(write_workflow(tmp_path, MULTI_LINE), "pr")
    unit = [c for c in commands if c.job == "t1-unit"]
    assert [c.name for c in unit] == [
        "Core tests and typing (1/2)",
        "Core tests and typing (2/2)",
    ]
    assert unit[0].argv[-2:] == ("-m", "not integration")
    assert unit[1].argv[-2:] == ("--project", "services/core/pyrightconfig.json")


def test_multi_line_step_with_other_commands_is_rejected(tmp_path: Path) -> None:
    text = MULTI_LINE.replace(
        "          uv run --project ci --locked pyright",
        "          rm -rf build\n          uv run --project ci --locked pyright",
    )
    with pytest.raises(WorkflowError, match="every line"):
        load_commands(write_workflow(tmp_path, text), "pr")
