from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import make_env
from mfgctl import __version__
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
