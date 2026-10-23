from __future__ import annotations

import shutil
from pathlib import Path

from conftest import FakeRunner, make_env
from mfgctl.bootstrap import render_text, run_bootstrap, sync_command
from mfgctl.doctor import Status
from mfgctl.probe import TIMED_OUT, Result

FIRST_RUN = Result(
    0, stderr="Creating virtual environment at: ci/.venv\nInstalled 36 packages in 24ms"
)
SECOND_RUN = Result(
    0, stderr="Resolved 39 packages in 13ms\nAudited 36 packages in 1ms"
)


def sync_key(repo: Path) -> tuple[str, ...]:
    return ("uv", "sync", "--project", str(repo / "ci"), "--locked")


def test_first_run_reports_changes(repo: Path) -> None:
    outcome = run_bootstrap(make_env(repo, {sync_key(repo): FIRST_RUN}))
    assert outcome.exit_code == 0
    assert outcome.changed
    assert "changes applied" in render_text(outcome, dry_run=False)


def test_second_run_is_idempotent(repo: Path) -> None:
    outcome = run_bootstrap(make_env(repo, {sync_key(repo): SECOND_RUN}))
    assert outcome.exit_code == 0
    assert not outcome.changed
    assert "no changes needed" in render_text(outcome, dry_run=False)


def test_dry_run_executes_no_sync(repo: Path) -> None:
    env = make_env(repo)
    outcome = run_bootstrap(env, dry_run=True)
    assert outcome.exit_code == 0
    assert isinstance(env.run, FakeRunner)
    assert tuple(sync_command(env)) not in env.run.calls
    assert "would run: uv sync" in render_text(outcome, dry_run=True)


def test_missing_environment_will_be_created(repo: Path) -> None:
    shutil.rmtree(repo / "ci" / ".venv")
    outcome = run_bootstrap(make_env(repo, {sync_key(repo): FIRST_RUN}))
    assert outcome.steps[2].detail.endswith("will be created")
    assert outcome.exit_code == 0


def test_unusable_environment_stops_without_deleting(
    repo: Path, tmp_path: Path
) -> None:
    python = repo / "ci" / ".venv" / "bin" / "python"
    python.unlink()
    python.symlink_to(tmp_path / "elsewhere" / "python")
    env = make_env(repo)
    outcome = run_bootstrap(env)
    assert outcome.exit_code == 1
    assert (repo / "ci" / ".venv").exists()  # nothing removed behind the user's back
    assert isinstance(env.run, FakeRunner)
    assert not any(call[:2] == ("uv", "sync") for call in env.run.calls)
    assert "nothing was removed" in render_text(outcome, dry_run=False)


def test_missing_uv_stops_before_sync(repo: Path) -> None:
    outcome = run_bootstrap(make_env(repo, {("uv", "--version"): Result(127)}))
    assert outcome.exit_code == 1
    assert [step.name for step in outcome.steps] == ["git", "uv"]


def test_failed_or_hung_sync_fails_with_remediation(repo: Path) -> None:
    stale = Result(2, stderr="error: The lockfile needs to be updated")
    for result in (stale, Result(TIMED_OUT, stderr="uv: timed out")):
        outcome = run_bootstrap(make_env(repo, {sync_key(repo): result}))
        sync = outcome.steps[-1]
        assert sync.status is Status.FAIL
        assert sync.remediation and "uv lock" in sync.remediation


def test_personal_environment_is_respected(repo: Path, tmp_path: Path) -> None:
    personal = tmp_path / "personal"
    env = make_env(repo, environ={"UV_PROJECT_ENVIRONMENT": str(personal)})
    outcome = run_bootstrap(env, dry_run=True)
    assert str(personal) in outcome.steps[2].detail
