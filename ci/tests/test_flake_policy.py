"""Negative and positive paths of flake governance (WP-CICD-001, TEST-DX-FLAKE)."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from check_flake_policy import find_retry_mechanisms, load_registry

TODAY = dt.date(2026, 10, 21)
VALID_ENTRY = """
  - test_id: "tools/x/tests/test_a.py::test_one"
    owner: Yavuz
    issue: "CAP-1"
    reason: "intermittent timeout"
    quarantined_on: 2026-10-20
    expires_on: 2026-10-30
    release_impact: "must be fixed before release gate"
"""


def registry(tmp_path: Path, entries: str = " []", max_days: int = 14) -> Path:
    path = tmp_path / "flaky_tests.yaml"
    body = entries if entries.startswith(" []") else "\n" + entries.strip("\n")
    path.write_text(
        "schema_version: cap-flaky-registry-v1\n"
        f"max_quarantine_days: {max_days}\n"
        f"entries:{body}\n",
        encoding="utf-8",
    )
    return path


def test_empty_registry_is_valid(tmp_path: Path) -> None:
    assert load_registry(registry(tmp_path), TODAY) == ([], [])


def test_repository_registry_is_valid() -> None:
    _, errors = load_registry(today=TODAY)
    assert errors == []


def test_complete_entry_is_accepted(tmp_path: Path) -> None:
    entries, errors = load_registry(registry(tmp_path, VALID_ENTRY), TODAY)
    assert errors == [] and [e.test_id for e in entries] == [
        "tools/x/tests/test_a.py::test_one"
    ]


def test_missing_owner_and_issue_are_rejected(tmp_path: Path) -> None:
    text = VALID_ENTRY.replace("    owner: Yavuz\n", "").replace(
        '    issue: "CAP-1"\n', ""
    )
    _, errors = load_registry(registry(tmp_path, text), TODAY)
    assert errors == ["entries[0]: missing owner, issue"]


def test_expired_quarantine_is_rejected(tmp_path: Path) -> None:
    _, errors = load_registry(registry(tmp_path, VALID_ENTRY), dt.date(2026, 11, 1))
    assert any("expired on 2026-10-30" in e for e in errors)


def test_overlong_quarantine_is_rejected(tmp_path: Path) -> None:
    _, errors = load_registry(registry(tmp_path, VALID_ENTRY, max_days=5), TODAY)
    assert any("longer than 5 days" in e for e in errors)


def test_duplicate_and_unknown_owner_are_rejected(tmp_path: Path) -> None:
    twice = VALID_ENTRY + VALID_ENTRY.replace("owner: Yavuz", "owner: Someone")
    _, errors = load_registry(registry(tmp_path, twice), TODAY)
    assert any("duplicate" in e for e in errors)
    assert any("unknown owner 'Someone'" in e for e in errors)


@pytest.mark.parametrize(
    "line",
    [
        "      - run: pytest --reruns 3",
        "        continue-on-error: true",
        "      - uses: nick-fields/retry@v3",
        'dev = ["pytest-rerunfailures"]',
    ],
)
def test_retry_until_green_is_rejected(tmp_path: Path, line: str) -> None:
    config = tmp_path / "workflow.yml"
    config.write_text(f"jobs:\n{line}\n", encoding="utf-8")
    assert len(find_retry_mechanisms([config], root=tmp_path)) == 1


def test_comments_do_not_trigger_retry_detection(tmp_path: Path) -> None:
    config = tmp_path / "workflow.yml"
    config.write_text(
        "# never use --reruns or continue-on-error: true\n", encoding="utf-8"
    )
    assert find_retry_mechanisms([config], root=tmp_path) == []


def test_plugin_runs_quarantined_test_as_xfail(
    pytester: pytest.Pytester, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_file = pytester.makepyfile(test_sample="def test_flaky():\n    assert False\n")  # pyright: ignore[reportUnknownMemberType]
    test_id = f"{test_file.resolve().as_posix()}::test_flaky"
    entry = VALID_ENTRY.replace("tools/x/tests/test_a.py::test_one", test_id)
    entry = entry.replace("2026-10-30", "2099-01-10").replace(
        "2026-10-20", "2099-01-01"
    )
    monkeypatch.setenv("CAP_FLAKY_REGISTRY", str(registry(tmp_path, entry)))
    result = pytester.runpytest_inprocess("-p", "pytest_quarantine")
    result.assert_outcomes(xfailed=1)
    result.stdout.fnmatch_lines(["*QUARANTINED*test_flaky*"])


def test_plugin_refuses_expired_registry(
    pytester: pytest.Pytester, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pytester.makepyfile(test_sample="def test_ok():\n    assert True\n")  # pyright: ignore[reportUnknownMemberType]
    expired = VALID_ENTRY.replace("2026-10-30", "2000-01-02").replace(
        "2026-10-20", "2000-01-01"
    )
    monkeypatch.setenv("CAP_FLAKY_REGISTRY", str(registry(tmp_path, expired)))
    result = pytester.runpytest_inprocess("-p", "pytest_quarantine")
    assert result.ret != 0
