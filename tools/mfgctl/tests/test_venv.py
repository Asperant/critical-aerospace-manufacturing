from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from conftest import make_env
from mfgctl import venv
from mfgctl.doctor import Status, check_venv


def test_default_location_is_ci_venv(repo: Path) -> None:
    assert venv.environment_path(repo, {}) == repo / "ci" / ".venv"


def test_uv_project_environment_absolute_and_relative(
    repo: Path, tmp_path: Path
) -> None:
    personal = tmp_path / "personal-env"
    assert venv.environment_path(repo, {venv.ENV_VAR: str(personal)}) == personal
    assert (
        venv.environment_path(repo, {venv.ENV_VAR: ".env-x"}) == repo / "ci" / ".env-x"
    )


def test_usable_environment_is_ok(repo: Path) -> None:
    assert check_venv(make_env(repo)).status is Status.OK


def test_missing_environment_warns_and_points_to_bootstrap(repo: Path) -> None:
    shutil.rmtree(repo / "ci" / ".venv")
    check = check_venv(make_env(repo))
    assert check.status is Status.WARN
    assert check.remediation and "mfgctl bootstrap" in check.remediation


def test_dangling_interpreter_link_fails(repo: Path, tmp_path: Path) -> None:
    python = repo / "ci" / ".venv" / "bin" / "python"
    python.unlink()
    python.symlink_to(tmp_path / "home-of-another-user" / "python3.11")
    check = check_venv(make_env(repo))
    assert check.status is Status.FAIL
    assert "does not resolve" in check.detail


@pytest.mark.skipif(os.geteuid() == 0, reason="root can execute any file")
def test_non_executable_interpreter_fails(repo: Path, tmp_path: Path) -> None:
    target = tmp_path / "not-executable"
    target.write_text("#!/bin/sh\n", encoding="utf-8")
    target.chmod(0o644)
    python = repo / "ci" / ".venv" / "bin" / "python"
    python.unlink()
    python.symlink_to(target)
    assert check_venv(make_env(repo)).status is Status.FAIL


def test_remediation_depends_on_who_owns_the_environment(repo: Path) -> None:
    path = repo / "ci" / ".venv"
    mine = venv.remediation(path, current_user=path.owner())
    assert mine.startswith("Remove the derived environment")
    theirs = venv.remediation(path, current_user="someone-else")
    assert venv.ENV_VAR in theirs and path.owner() in theirs
