"""``mfgctl trace`` wiring (WP-GOV-002): mfgctl runs the cap_trace command in the
repository root and returns its exit code unchanged.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from mfgctl import trace
from mfgctl.cli import app
from mfgctl.repo import ENV_ROOT
from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[3]
runner = CliRunner()


def test_run_passes_arguments_in_the_repository_root(tmp_path: Path) -> None:
    seen: list[tuple[list[str], Path]] = []

    def fake_main(args: list[str]) -> int:
        seen.append((args, Path.cwd()))
        return 7

    before = Path.cwd()
    code = trace.run(tmp_path, ["validate", "--json"], loader=lambda root: fake_main)
    assert code == 7
    assert seen == [(["validate", "--json"], tmp_path)]
    assert Path.cwd() == before


def test_missing_trace_tooling_is_reported(tmp_path: Path) -> None:
    with pytest.raises(trace.TraceUnavailableError):
        trace.load_main(tmp_path)


@pytest.mark.parametrize(
    ("argv", "code", "text"),
    [
        (["trace", "validate"], 0, "PASS"),
        (["trace", "requirement", "FR-GOV-009"], 0, "TEST-GOV-TRACELINT"),
        (["trace", "requirement", "FR-NOPE-001"], 2, ""),
        (["trace", "orphans"], 0, "without VERIFIED_BY: 0"),
    ],
)
def test_trace_commands_on_the_real_repository(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], code: int, text: str
) -> None:
    monkeypatch.setenv(ENV_ROOT, str(ROOT))
    result = runner.invoke(app, argv)
    assert result.exit_code == code, result.output
    assert text in result.output


def test_trace_outside_a_checkout_with_tools(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "AGENTS.md").write_text("a\n", "utf-8")
    (tmp_path / "docs/04_Work_Breakdown_Structure.md").write_text("w\n", "utf-8")
    monkeypatch.setenv(ENV_ROOT, str(tmp_path))
    result = runner.invoke(app, ["trace", "validate"])
    assert result.exit_code == 2
    assert "tools/trace/src/cap_trace not found" in result.output
    assert os.environ[ENV_ROOT] == str(tmp_path)
