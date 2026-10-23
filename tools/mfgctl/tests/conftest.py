from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest
from mfgctl.doctor import GIB, Environment
from mfgctl.probe import Result

HEALTHY: dict[tuple[str, ...], Result] = {
    ("git", "--version"): Result(0, "git version 2.43.0"),
    ("docker", "version", "--format", "{{.Server.Version}}"): Result(0, "27.3.1"),
    ("docker", "compose", "version", "--short"): Result(0, "2.29.7"),
    ("uv", "--version"): Result(0, "uv 0.12.13 (abc 2026-09-30)"),
}


class FakeRunner:
    """Answers commands from a table; records every call."""

    def __init__(
        self, root: Path, overrides: dict[tuple[str, ...], Result] | None = None
    ):
        self.table = dict(HEALTHY)
        self.table[("git", "-C", str(root), "rev-parse", "--is-inside-work-tree")] = (
            Result(0, "true")
        )
        self.table[("uv", "lock", "--locked", "--project", str(root / "ci"))] = Result(
            0
        )
        self.table.update(overrides or {})
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, args: Sequence[str], timeout: float) -> Result:
        key = tuple(args)
        self.calls.append(key)
        return self.table.get(key, Result(127, stderr=f"{args[0]}: command not found"))


def make_repo(root: Path, uv_pin: str | None = "0.12.13") -> Path:
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "AGENTS.md").write_text("agents\n", encoding="utf-8")
    (root / "docs" / "04_Work_Breakdown_Structure.md").write_text(
        "wbs\n", encoding="utf-8"
    )
    (root / "ci").mkdir(exist_ok=True)
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    pin = f'  UV_VERSION: "{uv_pin}"\n' if uv_pin else ""
    (workflows / "ci.yml").write_text(f"name: ci\nenv:\n{pin}", encoding="utf-8")
    return root


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path / "repo")


def make_env(
    root: Path,
    overrides: dict[tuple[str, ...], Result] | None = None,
    *,
    python: tuple[int, int, int] = (3, 11, 16),
    free_gib: float = 100,
    busy_ports: frozenset[int] = frozenset(),
) -> Environment:
    return Environment(
        root=root,
        run=FakeRunner(root, overrides),
        python_version=python,
        disk_free_bytes=lambda _path: int(free_gib * GIB),
        port_in_use=lambda port: port in busy_ports,
    )
