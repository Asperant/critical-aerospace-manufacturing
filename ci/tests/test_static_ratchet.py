"""Negative and positive paths of the static ratchet (WP-CICD-001)."""

from __future__ import annotations

import pytest
from static_ratchet import Snapshot, compare, tightened

TOOLS = {"ruff": "ruff 0.7.4", "pyright": "pyright 1.1.389"}


def snap(
    ruff: dict[str, dict[str, int]] | None = None,
    pyright: dict[str, dict[str, int]] | None = None,
    unformatted: list[str] | None = None,
    tools: dict[str, str] | None = None,
) -> Snapshot:
    return Snapshot(
        ruff=ruff or {},
        pyright=pyright or {},
        unformatted=unformatted or [],
        tools=dict(tools or TOOLS),
    )


def test_identical_snapshot_passes() -> None:
    base = snap(ruff={"a.py": {"F401": 2}}, unformatted=["a.py"])
    assert compare(base, base) == ([], [])


def test_more_findings_in_known_file_is_regression() -> None:
    regressions, _ = compare(
        snap(ruff={"a.py": {"F401": 2}}), snap(ruff={"a.py": {"F401": 3}})
    )
    assert regressions == ["ruff: a.py F401: 3 finding(s), allowed 2"]


def test_new_file_must_be_clean() -> None:
    regressions, _ = compare(
        snap(), snap(pyright={"new.py": {"reportArgumentType": 1}})
    )
    assert regressions == [
        "pyright: new.py reportArgumentType: 1 finding(s), allowed 0"
    ]


def test_new_rule_in_known_file_is_regression() -> None:
    regressions, _ = compare(
        snap(ruff={"a.py": {"F401": 5}}), snap(ruff={"a.py": {"B023": 1}})
    )
    assert "ruff: a.py B023: 1 finding(s), allowed 0" in regressions


def test_newly_unformatted_file_is_regression() -> None:
    regressions, _ = compare(
        snap(unformatted=["old.py"]), snap(unformatted=["old.py", "new.py"])
    )
    assert regressions == ["format: new.py is not formatted (`ruff format new.py`)"]


def test_tool_version_drift_is_regression() -> None:
    regressions, _ = compare(
        snap(), snap(tools={"ruff": "ruff 9.9.9", "pyright": TOOLS["pyright"]})
    )
    assert len(regressions) == 1 and "ruff: version" in regressions[0]


def test_fixed_findings_are_reported_as_loosened() -> None:
    _, loosened = compare(
        snap(ruff={"a.py": {"F401": 2}}, unformatted=["a.py"]), snap()
    )
    assert loosened == [
        "ruff: a.py F401: 0 < baseline 2",
        "format: a.py is now formatted",
    ]


def test_update_tightens_but_never_records_regressions() -> None:
    base = snap(ruff={"a.py": {"F401": 2}})
    assert tightened(base, snap(ruff={"a.py": {"F401": 1}})).ruff == {
        "a.py": {"F401": 1}
    }
    with pytest.raises(SystemExit):
        tightened(base, snap(ruff={"a.py": {"F401": 3}}))
