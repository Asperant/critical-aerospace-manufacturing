"""TEST-CICD-003-001: the migration stage's decisions, against a fake backend.

A diverged or unreadable database halts before anything is applied; a failed apply
halts before the rollout and says where the database was left; the target must be
reached; no error text carries a connection string.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import cap_release.__main__ as cli
import pytest
from cap_release.migrations import (
    CoreBackend,
    Entry,
    MigrationError,
    backend_from_environment,
    classify,
    expected_ledger,
    migration_for,
    run_stage,
)
from cap_release.registry import Migration, load_registry

MIGRATION = Migration(
    "manufacturing-core",
    "services/manufacturing-core/src/manufacturing_core/migrations",
)


class FakeBackend:
    def __init__(
        self,
        ledger: list[Entry] | None,
        *,
        apply_fails: str | None = None,
        unreadable: bool = False,
    ) -> None:
        self.current = ledger
        self.apply_fails = apply_fails
        self.unreadable = unreadable
        self.expected: list[Entry] = []
        self.applied_calls = 0
        self.partial = 0  # how many migrations a failing apply still commits

    def ledger(self) -> list[Entry] | None:
        if self.unreadable:
            raise MigrationError("the database could not be read (OperationalError)")
        return None if self.current is None else list(self.current)

    def apply(self) -> bool:
        self.applied_calls += 1
        done = len(self.current or [])
        if self.apply_fails:
            self.current = list(self.expected[: done + self.partial]) or None
            raise MigrationError(self.apply_fails)
        self.current = list(self.expected)
        return True


@pytest.fixture
def expected(repo: Path) -> list[Entry]:
    return expected_ledger(repo, MIGRATION)


def target(expected: list[Entry]) -> str:
    return f"manufacturing-core:{expected[-1].version}"


def stage(
    repo: Path, expected: list[Entry], backend: FakeBackend, wanted: str | None = None
) -> str:
    backend.expected = expected
    return run_stage(repo, MIGRATION, wanted or target(expected), backend)


def test_the_expected_ledger_is_every_script_in_version_order_with_its_checksum(
    expected: list[Entry],
) -> None:
    versions = [e.version for e in expected]
    assert versions == sorted(versions) and versions[0].startswith("0001")
    assert all(re.fullmatch(r"[0-9a-f]{64}", e.sha256) for e in expected)


def test_the_directory_and_the_cores_own_migration_list_agree(
    repo: Path, expected: list[Entry]
) -> None:
    """A script added to the directory but not to the tooling's list would never run."""
    source = (
        repo / "services/manufacturing-core/src/manufacturing_core/migrate.py"
    ).read_text("utf-8")
    listed = re.findall(r'\("(\d{4}_[a-z0-9_]+)", "migrations/', source)
    assert listed == [e.version for e in expected]


@pytest.mark.parametrize("ledger", [None, []])
def test_a_database_without_applied_migrations_is_empty(
    expected: list[Entry], ledger: list[Entry] | None
) -> None:
    state = classify(expected, ledger)
    assert state.state == "EMPTY" and list(state.pending) == [
        e.version for e in expected
    ]


def test_a_prefix_is_behind_and_the_full_ledger_is_current(
    expected: list[Entry],
) -> None:
    behind = classify(expected, expected[:2])
    assert behind.state == "BEHIND" and behind.applied == (
        expected[0].version,
        expected[1].version,
    )
    assert behind.pending[0] == expected[2].version
    current = classify(expected, expected)
    assert current.state == "CURRENT" and current.pending == ()


@pytest.mark.parametrize(
    ("mutate", "expect"),
    [
        (
            lambda ledger: [Entry("0001_other", ledger[0].sha256), *ledger[1:]],
            "expects",
        ),
        (
            lambda ledger: [Entry(ledger[0].version, "0" * 64), *ledger[1:]],
            "different checksum",
        ),
        (lambda ledger: [*ledger, Entry("9999_future", "1" * 64)], "does not know"),
        (lambda ledger: [ledger[1], ledger[0], *ledger[2:]], "expects"),
    ],
)
def test_a_diverged_ledger_is_never_applied_over(
    expected: list[Entry], mutate: Any, expect: str
) -> None:
    state = classify(expected, mutate(list(expected)))
    assert state.state == "DIVERGED" and expect in state.detail


def test_an_empty_database_is_migrated_to_the_target_and_checked_afterwards(
    repo: Path, expected: list[Entry]
) -> None:
    backend = FakeBackend(None)
    detail = stage(repo, expected, backend)
    assert backend.applied_calls == 1
    assert (
        detail.startswith("applied 0001")
        and f"database at {expected[-1].version}" in detail
    )


def test_a_database_behind_applies_only_what_is_pending(
    repo: Path, expected: list[Entry]
) -> None:
    backend = FakeBackend(expected[:-1])
    detail = stage(repo, expected, backend)
    assert (
        detail == f"applied {expected[-1].version}; database at {expected[-1].version}"
    )


def test_a_current_database_is_left_alone(repo: Path, expected: list[Entry]) -> None:
    backend = FakeBackend(list(expected))
    assert (
        "nothing to apply" in stage(repo, expected, backend)
        and backend.applied_calls == 0
    )


def test_a_diverged_database_halts_before_anything_is_applied(
    repo: Path, expected: list[Entry]
) -> None:
    backend = FakeBackend([Entry(expected[0].version, "0" * 64)])
    with pytest.raises(MigrationError, match="pre-check halted, nothing applied"):
        stage(repo, expected, backend)
    assert backend.applied_calls == 0


def test_an_unreadable_database_halts_before_anything_is_applied(
    repo: Path, expected: list[Entry]
) -> None:
    backend = FakeBackend(None, unreadable=True)
    with pytest.raises(MigrationError, match="pre-check failed, nothing applied"):
        stage(repo, expected, backend)
    assert backend.applied_calls == 0


def test_a_failed_apply_halts_and_says_where_the_database_was_left(
    repo: Path, expected: list[Entry]
) -> None:
    backend = FakeBackend(
        expected[:1], apply_fails="the migration failed (DatabaseError)"
    )
    backend.partial = 2
    with pytest.raises(MigrationError) as raised:
        stage(repo, expected, backend)
    text = str(raised.value)
    assert (
        "the migration failed" in text
        and expected[2].version in text
        and "not reverted" in text
    )


def test_a_failed_first_apply_reports_that_nothing_was_applied(
    repo: Path, expected: list[Entry]
) -> None:
    backend = FakeBackend(
        None, apply_fails="the migration failed (InsufficientPrivilege)"
    )
    with pytest.raises(MigrationError, match="no migration"):
        stage(repo, expected, backend)


def test_a_database_that_is_not_at_the_target_after_the_apply_fails_the_stage(
    repo: Path, expected: list[Entry]
) -> None:
    class Partial(FakeBackend):
        def apply(self) -> bool:
            self.applied_calls += 1
            self.current = list(self.expected[:2])
            return True

    backend = Partial(None)
    with pytest.raises(MigrationError, match="post-check failed"):
        stage(repo, expected, backend)


def test_a_target_that_is_not_this_checkouts_head_halts(
    repo: Path, expected: list[Entry]
) -> None:
    backend = FakeBackend(None)
    with pytest.raises(MigrationError, match="this checkout's head"):
        stage(repo, expected, backend, wanted="manufacturing-core:0001_domain")
    assert backend.applied_calls == 0


def test_a_target_with_no_declared_migration_set_is_refused(repo: Path) -> None:
    with pytest.raises(MigrationError, match="declares no such migration set"):
        migration_for(load_registry(repo), "billing:0003_x")
    assert (
        migration_for(load_registry(repo), "manufacturing-core:0007_lot_lineage")
        == MIGRATION
    )


def test_the_environment_supplies_the_identity_and_its_absence_fails_closed(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("CAP_MIGRATION_DSN", "CAP_RUNTIME_ROLE"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(
        MigrationError, match="needs CAP_MIGRATION_DSN and CAP_RUNTIME_ROLE"
    ):
        backend_from_environment(repo)
    monkeypatch.setenv("CAP_MIGRATION_DSN", "postgresql://migrator:hunter2@db/x")
    monkeypatch.setenv("CAP_RUNTIME_ROLE", "runtime")
    assert "hunter2" not in repr(backend_from_environment(repo))


def fake_core(tmp_path: Path, body: str) -> Path:
    """A throw-away checkout whose migration tooling raises on purpose."""
    package = tmp_path / "services/manufacturing-core/src/manufacturing_core"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "migrate.py").write_text(body)
    return tmp_path


@pytest.mark.parametrize(
    ("body", "call", "expect"),
    [
        (
            "def status(dsn):\n    raise RuntimeError(dsn)\n",
            "ledger",
            "could not be read (RuntimeError)",
        ),
        (
            "def migrate(dsn, role):\n    raise RuntimeError(dsn)\n",
            "apply",
            "the migration failed (RuntimeError)",
        ),
        (
            "def migrate(dsn, role):\n    raise ValueError('migration and runtime roles must differ')\n",
            "apply",
            "migration and runtime roles must differ",
        ),
    ],
)
def test_the_core_backend_never_surfaces_a_connection_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str, call: str, expect: str
) -> None:
    for name in [m for m in sys.modules if m.startswith("manufacturing_core")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "path", list(sys.path))
    root = fake_core(tmp_path, body)
    backend = CoreBackend(root, "postgresql://migrator:hunter2@db/x", "runtime")
    with pytest.raises(MigrationError) as raised:
        getattr(backend, call)()
    assert expect in str(raised.value) and "hunter2" not in str(raised.value)
    for name in [m for m in sys.modules if m.startswith("manufacturing_core")]:
        monkeypatch.delitem(sys.modules, name)


def test_a_missing_core_tooling_is_a_clear_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in [m for m in sys.modules if m.startswith("manufacturing_core")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(
        sys, "path", [p for p in sys.path if "manufacturing-core" not in p]
    )
    with pytest.raises(MigrationError, match="cannot be imported"):
        CoreBackend(tmp_path, "x", "r").ledger()


@pytest.mark.parametrize(
    ("ledger", "unreadable", "code", "state"),
    [
        ("current", False, 0, "CURRENT"),
        ("behind", False, 1, "BEHIND"),
        (None, False, 1, "EMPTY"),
        ("diverged", False, 2, "DIVERGED"),
        (None, True, 2, "UNREADABLE"),
    ],
)
def test_migration_status_reports_the_state_with_a_meaningful_exit_code(
    repo: Path,
    expected: list[Entry],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    ledger: str | None,
    unreadable: bool,
    code: int,
    state: str,
) -> None:
    rows = {
        "current": list(expected),
        "behind": expected[:-1],
        "diverged": [Entry(expected[0].version, "0" * 64)],
        None: None,
    }[ledger]
    backend = FakeBackend(rows, unreadable=unreadable)
    monkeypatch.setattr(cli, "backend_from_environment", lambda root: backend)
    assert cli.cmd_migration_status(None) == code  # type: ignore[arg-type]
    printed = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert printed["state"] == state and printed["component"] == "manufacturing-core"
