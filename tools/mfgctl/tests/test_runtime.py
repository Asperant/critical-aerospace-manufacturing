from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest
from mfgctl import probe
from mfgctl.cli import app
from mfgctl.registry import DEFAULT_PATH
from mfgctl.repo import ENV_ROOT
from typer.testing import CliRunner

runner = CliRunner()
EXAMPLE = Path(__file__).resolve().parents[1] / "schemas" / "capabilities.json"
COMPOSE = ("docker", "compose", "-f", "infra/compose/compose.yaml")


class FakeStream:
    def __init__(self, code: int = 0) -> None:
        self.code = code
        self.calls: list[tuple[str, ...]] = []

    def __call__(
        self, args: Sequence[str], env: Mapping[str, str], cwd: Path, timeout: float
    ) -> int:
        self.calls.append(tuple(args))
        return self.code


@pytest.fixture
def stream(monkeypatch: pytest.MonkeyPatch, repo: Path) -> FakeStream:
    monkeypatch.setenv(ENV_ROOT, str(repo))
    fake = FakeStream()
    monkeypatch.setattr(probe, "run_streaming", fake)
    return fake


@pytest.fixture
def with_registry(repo: Path) -> Path:
    target = repo / DEFAULT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "args",
    [
        ["profile", "list"],
        ["up", "core"],
        ["down", "core"],
        ["status"],
        ["smoke", "platform"],
        ["scenario", "list"],
        ["scenario", "run", "GS-01"],
    ],
)
def test_without_registry_nothing_runs_and_exit_is_two(
    stream: FakeStream, args: list[str]
) -> None:
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "WP-PLAT-001" in result.output
    assert stream.calls == []


def test_up_and_down_build_compose_profile_commands(
    stream: FakeStream, with_registry: Path
) -> None:
    assert runner.invoke(app, ["up", "core"]).exit_code == 0
    assert runner.invoke(app, ["down", "core"]).exit_code == 0
    assert runner.invoke(app, ["status"]).exit_code == 0
    assert stream.calls == [
        (*COMPOSE, "--profile", "core", "up", "--detach", "--wait"),
        (*COMPOSE, "--profile", "core", "down"),
        (*COMPOSE, "ps", "--all"),
    ]


def test_smoke_and_scenario_run_declared_argv(
    stream: FakeStream, with_registry: Path
) -> None:
    smoke = runner.invoke(app, ["smoke", "platform"])
    assert smoke.exit_code == 0 and "smoke platform: PASS" in smoke.output
    assert runner.invoke(app, ["scenario", "run", "GS-01"]).exit_code == 0
    declared = json.loads(with_registry.read_text(encoding="utf-8"))
    assert stream.calls == [
        tuple(declared["capabilities"][0]["smoke"]),
        tuple(declared["scenarios"][0]["command"]),
    ]


def test_failing_smoke_exits_one(stream: FakeStream, with_registry: Path) -> None:
    stream.code = 3
    result = runner.invoke(app, ["smoke", "platform"])
    assert result.exit_code == 1
    assert "FAIL (exit 3)" in result.output


def test_unknown_names_exit_two_without_running(
    stream: FakeStream, with_registry: Path
) -> None:
    for args in (["up", "gpu"], ["smoke", "vision"], ["scenario", "run", "GS-99"]):
        result = runner.invoke(app, args)
        assert result.exit_code == 2
        assert "known:" in result.output
    assert stream.calls == []


def test_listings(stream: FakeStream, with_registry: Path) -> None:
    profiles = runner.invoke(app, ["profile", "list"])
    assert profiles.exit_code == 0
    assert "core" in profiles.output and "smoke: platform" in profiles.output
    scenarios = runner.invoke(app, ["scenario", "list"])
    assert "GS-01" in scenarios.output


def test_smoke_and_up_record_timings_for_dx_targets(
    stream: FakeStream, with_registry: Path, isolated_state: Path
) -> None:
    runner.invoke(app, ["smoke", "platform"])
    runner.invoke(app, ["up", "core"])
    lines = (isolated_state / "timings.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["command"] for line in lines] == ["smoke", "up"]
