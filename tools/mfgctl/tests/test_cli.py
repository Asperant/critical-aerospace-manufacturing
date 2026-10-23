from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import make_env
from mfgctl import __version__, probe
from mfgctl import doctor as doctor_module
from mfgctl.cli import app
from mfgctl.probe import Result
from mfgctl.repo import ENV_ROOT
from typer.testing import CliRunner

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"mfgctl {__version__}"


def test_help_lists_doctor() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doctor" in result.output


@pytest.fixture
def fake_machine(monkeypatch: pytest.MonkeyPatch, repo: Path):
    def install(overrides: dict[tuple[str, ...], Result] | None = None) -> None:
        monkeypatch.setenv(ENV_ROOT, str(repo))
        monkeypatch.setattr(
            doctor_module, "default_environment", lambda root: make_env(root, overrides)
        )

    return install


def test_doctor_json_exit_zero_when_healthy(fake_machine) -> None:
    fake_machine()
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["status"] == "OK"


def test_doctor_exit_one_on_failure(fake_machine) -> None:
    fake_machine(
        {("docker", "version", "--format", "{{.Server.Version}}"): Result(127)}
    )
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert "FAIL  docker" in result.output


def test_doctor_outside_repository_exits_two(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(ENV_ROOT, raising=False)
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 2
    assert "no repository root" in result.output


def test_every_command_records_its_timing(fake_machine, isolated_state: Path) -> None:
    fake_machine()
    runner.invoke(app, ["doctor"])
    runner.invoke(app, ["bootstrap", "--dry-run"])
    lines = (isolated_state / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    commands = [json.loads(line)["command"] for line in lines]
    assert commands == ["doctor", "bootstrap --dry-run"]
    summary = runner.invoke(app, ["timings"])
    assert summary.exit_code == 0
    assert "doctor" in summary.output and "within target" in summary.output


def test_bootstrap_dry_run_changes_nothing(fake_machine) -> None:
    fake_machine()
    result = runner.invoke(app, ["bootstrap", "--dry-run"])
    assert result.exit_code == 0
    assert "nothing was changed" in result.output


def test_check_rejects_conflicting_tiers() -> None:
    result = runner.invoke(app, ["check", "--fast", "--pr"])
    assert result.exit_code == 2


def test_check_runs_workflow_commands(
    fake_machine, monkeypatch: pytest.MonkeyPatch, repo: Path
) -> None:
    fake_machine()
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "jobs:\n  static:\n    name: t1-static\n    steps:\n"
        "      - name: Ratchet\n        run: uv run --project ci python ratchet.py\n",
        encoding="utf-8",
    )
    calls: list[tuple[str, ...]] = []

    def fake_stream(args, env, cwd, timeout) -> int:
        calls.append(tuple(args))
        return 0

    monkeypatch.setattr(probe, "run_streaming", fake_stream)
    result = runner.invoke(app, ["check"])
    assert result.exit_code == 0
    assert calls == [("uv", "run", "--project", "ci", "python", "ratchet.py")]
    assert "PASS    t1-static" in result.output


def test_check_reports_workflow_drift_with_exit_two(fake_machine, repo: Path) -> None:
    fake_machine()
    (repo / ".github" / "workflows" / "ci.yml").write_text(
        "jobs: {}\n", encoding="utf-8"
    )
    result = runner.invoke(app, ["check", "--pr"])
    assert result.exit_code == 2
    assert "no longer defines job" in result.output
