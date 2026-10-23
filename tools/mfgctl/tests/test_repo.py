from __future__ import annotations

from pathlib import Path

import pytest
from conftest import make_repo
from mfgctl.repo import ENV_ROOT, RepoNotFoundError, find_repo_root


def test_finds_root_from_nested_directory(repo: Path) -> None:
    nested = repo / "tools" / "mfgctl" / "src"
    nested.mkdir(parents=True)
    assert find_repo_root(nested, {}) == repo.resolve()


def test_environment_override_wins_over_current_directory(
    repo: Path, tmp_path: Path
) -> None:
    other = make_repo(tmp_path / "other")
    assert find_repo_root(repo, {ENV_ROOT: str(other)}) == other.resolve()


def test_invalid_override_fails_instead_of_falling_back(
    repo: Path, tmp_path: Path
) -> None:
    with pytest.raises(RepoNotFoundError, match=ENV_ROOT):
        find_repo_root(repo, {ENV_ROOT: str(tmp_path / "missing")})


def test_outside_repository_fails(tmp_path: Path) -> None:
    with pytest.raises(RepoNotFoundError, match="no repository root"):
        find_repo_root(tmp_path, {})


def test_one_marker_alone_is_not_a_root(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("only one marker\n", encoding="utf-8")
    with pytest.raises(RepoNotFoundError):
        find_repo_root(tmp_path, {})
