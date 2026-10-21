"""WP-CICD-001 pytest plugin: apply ``ci/flaky_tests.yaml`` to a test run.

Load with ``-p pytest_quarantine`` (``ci`` and ``ci/scripts`` on ``PYTHONPATH``). Quarantined
tests still execute; a failure is reported as XFAIL (non-strict) instead of
failing the gate. An invalid or expired registry stops the run, so a
quarantine can never outlive its expiry silently. ``CAP_FLAKY_REGISTRY``
overrides the registry path (used by the plugin's own tests).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from _pytest.terminal import TerminalReporter
from check_flake_policy import REGISTRY_PATH, REPO_ROOT, Quarantine, load_registry

_ACTIVE = pytest.StashKey[dict[str, Quarantine]]()
_APPLIED = pytest.StashKey[list[str]]()


def _registry_path() -> Path:
    override = os.environ.get("CAP_FLAKY_REGISTRY")
    return Path(override) if override else REGISTRY_PATH


def _repo_test_id(item: pytest.Item) -> str:
    path = Path(str(item.path)).resolve()
    try:
        relative = path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        relative = path.as_posix()
    suffix = item.nodeid.split("::", 1)[1] if "::" in item.nodeid else item.name
    return f"{relative}::{suffix}"


def pytest_configure(config: pytest.Config) -> None:
    entries, errors = load_registry(_registry_path())
    if errors:
        raise pytest.UsageError(
            "Invalid flaky-test registry:\n" + "\n".join(f"  {e}" for e in errors)
        )
    config.stash[_ACTIVE] = {entry.test_id: entry for entry in entries}
    config.stash[_APPLIED] = []


def pytest_collection_modifyitems(
    session: pytest.Session, config: pytest.Config, items: list[pytest.Item]
) -> None:
    active = config.stash[_ACTIVE]
    for item in items:
        test_id = _repo_test_id(item)
        entry = active.get(test_id) or active.get(test_id.split("[", 1)[0])
        if entry is None:
            continue
        item.add_marker(
            pytest.mark.xfail(
                strict=False,
                reason=(
                    f"QUARANTINED {entry.issue} owner={entry.owner} "
                    f"until {entry.expires_on.isoformat()}: {entry.reason}"
                ),
            )
        )
        config.stash[_APPLIED].append(test_id)


def pytest_terminal_summary(
    terminalreporter: TerminalReporter, config: pytest.Config
) -> None:
    no_entries: dict[str, Quarantine] = {}
    no_ids: list[str] = []
    active = config.stash.get(_ACTIVE, no_entries)
    applied = config.stash.get(_APPLIED, no_ids)
    terminalreporter.write_sep("-", "flaky-test quarantine (ci/flaky_tests.yaml)")
    terminalreporter.write_line(
        f"{len(active)} registry entr(y/ies); {len(applied)} applied in this run"
    )
    for test_id in applied:
        terminalreporter.write_line(f"  QUARANTINED {test_id}")
